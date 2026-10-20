# T08 — Concurrent local audit appends

Implemented locally, 2026-10-19. No new record schema, history rewrite, remote
deployment or change to decision thresholds.

## Supported writer contract

`RecordWriter(path).append(record)` supports cooperating threads and processes
sharing **one regular file on a local POSIX filesystem** with working `flock`,
file `fsync` and directory `fsync`. Every writer must use this contract. Windows,
network filesystems, object stores and distributed multi-host writers are not
supported by this implementation. Hosts needing those environments must provide
a separately validated transactional audit store.

Each append first deep-copies and validates its input (including schema/replay
checks and missing event ID/timestamp), without creating or modifying a log on
validation failure. It then opens the file and takes an exclusive advisory lock on that inode.
While holding it, the writer:

1. Reads and verifies the whole existing chain on the same descriptor.
2. Rejects a malformed, unhashed, broken-link or unterminated tail without
   modifying existing bytes. It never scans past damage or repairs it.
3. Finalizes the privately held, validated record by linking to the actual
   current head and recomputing its hash. No caller-owned nested inputs are reused.
4. Serializes one complete UTF-8 JSON line and appends it directly through
   `os.write`. There is no buffered write left to flush after unlocking.
5. Flushes and `fsync`s the log, then `fsync`s the containing directory before
   returning the finalized record and releasing the lock.

The constructor stores only an absolute path; it does not cache a predecessor.
Two previously constructed writers cannot append from the same stale head.
Separate opens also serialize threads sharing a single `RecordWriter` instance.
The lock covers existing-chain verification, finalization and synchronization,
not just the write syscall. New-record input validation happens before locking.

`verify_chain`, `checkpoint` and `record_count` use shared locks, so they do not
mistake a cooperating writer's in-flight append for tampering. `record_count`
reports a verified current snapshot, not an immutable ordinal for an earlier
append. A count request refuses a damaged log rather than counting past it.

## Framing, failure and recovery

New records always end with a newline. A final JSON object with a valid hash but
no newline is still an incomplete frame and is refused. Invalid UTF-8 and JSON
scalars/arrays return a `broken` verification result rather than crashing the
verifier. Existing newline-terminated blank lines remain tolerated; an empty
file can receive a first record but is not a verified nonempty chain.

A short write or storage error raises an exception. **An exception is not proof
that nothing was appended.** The record may be partially written, fully written
but not synchronized, or synchronized before a later directory-sync/response
failure. Partial bytes are retained as evidence; automatic truncation, rollback,
re-chaining or blind retry is forbidden by this contract.

The host must supply a stable event/request ID before append and reconcile an
uncertain result against its durable records before retrying. This writer does
not deduplicate IDs or implement exactly-once delivery. Host retry coordination
and idempotency must handle concurrent requests as well as lost responses.
On damage, stop producers, preserve the file and independently held checkpoint,
and use an authorized recovery procedure. No repair command is introduced here.

## Storage and operational responsibilities

- Success means the OS accepted file and parent-directory synchronization, not
  that physical media, remote replication or power-loss recovery was tested.
  The parent directory must already exist. Filesystem/hardware durability and
  backup/retention remain host responsibilities.
- `/tmp` and ephemeral container disks remain disposable even after `fsync`.
  Configure durable host storage before claiming retained audit evidence.
- All participating writers/readers must respect the lock. Do not unlink,
  replace, rotate, truncate or edit the file while any worker can access it;
  inode locks cannot coordinate a replacement file or a non-cooperating writer.
  Stop all workers before changing storage paths and retain the old chain.
- Locks block while another operation holds them. The host owns timeouts,
  worker supervision and recovery; terminating a process releases its kernel
  locks but may leave an incomplete append. Do not treat a timeout as success.
- A full-chain scan/hash on each append is deliberately conservative and costs
  O(number of prior records). High-volume throughput and target-host capacity
  have not been benchmarked. Do not infer a production performance guarantee.
- The API's inference lock remains: safe audit appends do not make shared model
  instances safe for concurrent inference.

An unanchored chain still cannot detect an attacker recomputing every hash or
deleting a tail. Keep a checkpoint outside the log's trust domain. Existing
anchored rewrite/truncation checks remain in effect. Local locking adds no
authentication, signatures, access control or regulatory compliance claim.

## Acceptance tests

`tests/test_records_concurrency.py` covers two already-constructed writers,
12 overlapping threads on one writer, four spawned processes writing eight
unique events each, and a post-restart append with all hashes/counts intact.
Bounded barriers force overlap. It also covers malformed/torn tails with exact
byte preservation, short writes, file/directory sync failures, synchronization
order and shared-lock verification/checkpoint readers.

`tests/test_records_chain.py` retains edit, reorder, full rewrite,
anchored rewrite, anchored truncation and historical-example checks. Existing
schema/replay/model-approval regression tests run against the transactional writer.
