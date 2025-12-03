#!/bin/sh

show_help() {
    cat << 'EOF'

╔════════════════════════════════════════════════════════════════════════════╗
║                         REDIS CLI HELPER SCRIPT                            ║
╚════════════════════════════════════════════════════════════════════════════╝

USAGE:
  ./redis.sh              Connect to Redis using REDIS_URL environment variable
  ./redis.sh --help       Show this help message

ALTERNATIVE CONNECTION:
  redis-cli -h localhost -p 6379

╔════════════════════════════════════════════════════════════════════════════╗
║                            QUICK COMMANDS                                  ║
╚════════════════════════════════════════════════════════════════════════════╝
 
  Help:
    HELP @<group>                 To get a list of commands in <group>
    HELP <command>                For help on <command>
    HELP <tab>                    To get a list of commands in <tab>

  See all keys:
    KEYS *                        Show all keys (caution in production!)
    SCAN 0                        Safer alternative that doesn't block

  Get key value:
    GET key_name                  Get value of a specific key

  Delete key:
    DEL key_name                  Delete a specific key

  Check if key exists:
    EXISTS key_name               Returns 1 if exists, 0 if not

  Get key type:
    TYPE key_name                 Returns type (string, list, set, hash, zset)

  Set key with expiration:
    SETEX key_name 3600 "value"   Set key with 3600 seconds (1 hour) expiration

  Check time to live:
    TTL key_name                  Get remaining seconds (-1=no expiry, -2=not exist)

  Get all hash fields:
    HGETALL key_name              Get all fields and values from a hash

  Monitor all commands:
    MONITOR                       Watch all commands in real-time (Ctrl+C to stop)

  Get database info:
    INFO                          Get server information
    DBSIZE                        Get number of keys in current database

  Clear database:
    FLUSHDB                       Delete all keys in current DB (use with caution!)
    FLUSHALL                      Delete all keys in all DBs (extreme caution!)

╔════════════════════════════════════════════════════════════════════════════╗
║                      BASIC REDIS COMMANDS REFERENCE                        ║
╚════════════════════════════════════════════════════════════════════════════╝

┌─ CONNECTION & SERVER ──────────────────────────────────────────────────────┐
│ redis-cli                       Connect to Redis                           │
│ redis-cli -h host -p port       Connect to specific host/port              │
│ PING                            Test connection (returns PONG)             │
│ AUTH password                   Authenticate                               │
│ SELECT index                    Select database (0-15)                     │
│ QUIT                            Close connection                           │
└────────────────────────────────────────────────────────────────────────────┘

┌─ STRING OPERATIONS ────────────────────────────────────────────────────────┐
│ SET key value                   Set key to value                           │
│ GET key                         Get value of key                           │
│ DEL key                         Delete key                                 │
│ EXISTS key                      Check if key exists                        │
│ EXPIRE key seconds              Set expiration time                        │
│ TTL key                         Get remaining time to live                 │
│ SETEX key seconds value         Set with expiration                        │
│ MSET key1 val1 key2 val2        Set multiple keys                          │
│ MGET key1 key2                  Get multiple keys                          │
│ INCR key                        Increment integer value                    │
│ DECR key                        Decrement integer value                    │
└────────────────────────────────────────────────────────────────────────────┘

┌─ LIST OPERATIONS ──────────────────────────────────────────────────────────┐
│ LPUSH key value                 Push to left (head)                        │
│ RPUSH key value                 Push to right (tail)                       │
│ LPOP key                        Pop from left                              │
│ RPOP key                        Pop from right                             │
│ LRANGE key start stop           Get range (0 -1 for all)                   │
│ LLEN key                        Get list length                            │
└────────────────────────────────────────────────────────────────────────────┘

┌─ SET OPERATIONS ───────────────────────────────────────────────────────────┐
│ SADD key member                 Add member to set                          │
│ SREM key member                 Remove member from set                     │
│ SMEMBERS key                    Get all members                            │
│ SISMEMBER key member            Check if member exists                     │
│ SCARD key                       Get set size                               │
└────────────────────────────────────────────────────────────────────────────┘

┌─ HASH OPERATIONS ──────────────────────────────────────────────────────────┐
│ HSET key field value            Set hash field                             │
│ HGET key field                  Get hash field                             │
│ HGETALL key                     Get all fields and values                  │
│ HDEL key field                  Delete hash field                          │
│ HEXISTS key field               Check if field exists                      │
│ HKEYS key                       Get all field names                        │
│ HVALS key                       Get all values                             │
└────────────────────────────────────────────────────────────────────────────┘

┌─ SORTED SET OPERATIONS ────────────────────────────────────────────────────┐
│ ZADD key score member           Add member with score                      │
│ ZRANGE key start stop           Get range by index                         │
│ ZRANGEBYSCORE key min max       Get range by score                         │
│ ZREM key member                 Remove member                              │
│ ZCARD key                       Get sorted set size                        │
└────────────────────────────────────────────────────────────────────────────┘

┌─ KEY MANAGEMENT ───────────────────────────────────────────────────────────┐
│ KEYS pattern                    Find keys (use * for all)                  │
│ SCAN cursor                     Iterate keys (safer than KEYS)             │
│ TYPE key                        Get key type                               │
│ RENAME key newkey               Rename key                                 │
│ FLUSHDB                         Delete all keys in current DB              │
│ FLUSHALL                        Delete all keys in all DBs                 │
└────────────────────────────────────────────────────────────────────────────┘

┌─ PUB/SUB (Channels) ───────────────────────────────────────────────────────┐
│ PUBLISH channel message         Publish message to channel                 │
│ SUBSCRIBE channel               Subscribe to channel(s)                    │
│ UNSUBSCRIBE channel             Unsubscribe from channel                   │
│ PSUBSCRIBE pattern              Subscribe to channels matching pattern     │
│ PUBSUB CHANNELS                 List active channels                       │
│                                                                            │
│ What is a channel?                                                         │
│   A named communication pathway for Pub/Sub messaging pattern.             │
│   Messages are NOT stored - only delivered to active subscribers.          │
│                                                                            │
│ Real-world example:                                                        │
│   Terminal 1 (Subscriber):                                                 │
│     SUBSCRIBE chat:room1        # Listen to chat:room1 channel             │
│                                                                            │
│   Terminal 2 (Publisher):                                                  │
│     PUBLISH chat:room1 "Hello!" # Send message to chat:room1               │
│                                                                            │
│   Use cases: Chat apps, notifications, event broadcasting                  │
└────────────────────────────────────────────────────────────────────────────┘

┌─ TRANSACTIONS ─────────────────────────────────────────────────────────────┐
│ MULTI                           Start transaction                          │
│ EXEC                            Execute transaction                        │
│ DISCARD                         Cancel transaction                         │
│ WATCH key                       Watch key for changes                      │
└────────────────────────────────────────────────────────────────────────────┘

┌─ INFO & MONITORING ────────────────────────────────────────────────────────┐
│ INFO                            Server information                         │
│ MONITOR                         Watch all commands in real-time            │
│ DBSIZE                          Get number of keys                         │
│ CONFIG GET parameter            Get config parameter                       │
└────────────────────────────────────────────────────────────────────────────┘

┌─ STREAM OPERATIONS (X commands) ───────────────────────────────────────────┐
│ What is a Redis Stream?                                                    │
│   A log-like data structure for storing ordered entries with unique IDs.   │
│   Each entry has an ID (timestamp-sequence) and field-value pairs.         │
│   Perfect for event sourcing, message queues, and activity feeds.          │
│                                                                            │
│ Entry ID format: timestamp-sequence (e.g., 1763006032172-0)                │
│   - timestamp: milliseconds since epoch                                    │
│   - sequence: counter for entries in same millisecond                      │
│                                                                            │
│ Why "X" prefix?                                                            │
│   X stands for "eXtended" or represents the stream timeline/axis.          │
│   Distinguishes from other data structures (L=list, S=set, Z=sorted set)   │
│                                                                            │
│ XADD key [MAXLEN ~] * field value   Add entry to stream                    │
│   Example: XADD mystream * text "hello" user "alice"                       │
│   Returns: Entry ID like "1763006032172-0"                                 │
│   Note: "*" means auto-generate ID (recommended). You can specify custom:  │
│         XADD mystream 1234567890000-0 text "hello"                         │
│         But "*" ensures IDs are always increasing and unique.              │
│                                                                            │
│ XRANGE key start end [COUNT n]      Read range of entries                  │
│   Example: XRANGE mystream - +                    # All entries            │
│   Example: XRANGE mystream 1763006032172-0 +      # From specific ID       │
│   Special IDs: "-" (start), "+" (end), "0-0" (beginning)                   │
│                                                                            │
│ XREVRANGE key end start [COUNT n]   Read range in reverse order            │
│   Example: XREVRANGE mystream + - COUNT 10        # Last 10 entries        │
│                                                                            │
│ XREAD [BLOCK ms] STREAMS key ID     Read from stream(s), optionally block  │
│   Example: XREAD STREAMS mystream 0-0             # Read all               │
│   Example: XREAD BLOCK 5000 STREAMS mystream $    # Wait for new           │
│   Special ID: "$" (only new entries after this command)                    │
│                                                                            │
│ XLEN key                            Get number of entries in stream        │
│   Example: XLEN mystream                                                   │
│                                                                            │
│ XINFO STREAM key                    Get stream information                 │
│   Example: XINFO STREAM mystream                                           │
│   Shows: length, first/last entry, consumer groups, etc.                   │
│                                                                            │
│ XTRIM key MAXLEN [~] count          Trim stream to specified length        │
│   Example: XTRIM mystream MAXLEN ~ 1000           # Keep ~1000 entries     │
│   "~" makes it approximate (faster, less precise)                          │
│                                                                            │
│ XDEL key ID [ID ...]                Delete specific entries                │
│   Example: XDEL mystream 1763006032172-0                                   │
│                                                                            │
│ Setting TTL on streams:                                                    │
│   EXPIRE key seconds                Set/update TTL on stream               │
│     Example: EXPIRE run:demo-123 900           # Set TTL to 900 seconds    │
│     Example: EXPIRE run:demo-123 1800          # Update TTL to 1800s       │
│     Note: Each EXPIRE call overwrites the previous TTL                     │
│                                                                            │
│   TTL key                           Check remaining TTL                    │
│     Returns: seconds remaining, -1 (no expiry), -2 (key doesn't exist)     │
│                                                                            │
│   EXPIREAT key timestamp            Set expiry at specific Unix timestamp  │
│     Example: EXPIREAT run:demo-123 1763100000                              │
│                                                                            │
│   PERSIST key                       Remove expiry (make key permanent)     │
│     Example: PERSIST run:demo-123                                          │
│                                                                            │
│ Real-world example workflow:                                               │
│   # Producer adds entries                                                  │
│   XADD run:demo-123 * text "chunk 1"                                       │
│   XADD run:demo-123 * text "chunk 2"                                       │
│   XADD run:demo-123 * type "end"                                           │
│                                                                            │
│   # Consumer reads entries                                                 │
│   XRANGE run:demo-123 - +              # Read all entries                  │
│   XLEN run:demo-123                    # Check stream length               │
│   XINFO STREAM run:demo-123            # Get stream details                │
│                                                                            │
│   # Cleanup                                                                │
│   XTRIM run:demo-123 MAXLEN ~ 100      # Keep only last ~100 entries       │
│   DEL run:demo-123                     # Delete entire stream              │
│                                                                            │
│ Use cases:                                                                 │
│   - Chat/streaming applications (chunked data delivery)                    │
│   - Event sourcing (ordered event log)                                     │
│   - Activity feeds (user actions timeline)                                 │
│   - Message queues (with consumer groups)                                  │
│   - Real-time analytics (time-series data)                                 │
│                                                                            │
│ Streams vs Pub/Sub vs Lists:                                               │
│   Streams:  Persistent, ordered, replayable, multiple consumers            │
│   Pub/Sub:  Ephemeral, fire-and-forget, no history                         │
│   Lists:    Persistent, ordered, but no unique IDs or time-based queries   │
└────────────────────────────────────────────────────────────────────────────┘

┌─ STREAM CONSUMER GROUPS ───────────────────────────────────────────────────┐
│ What is a Consumer Group?                                                  │
│   A mechanism for distributing stream messages among multiple consumers.   │
│   Each message is delivered to only ONE consumer in the group.             │
│   Tracks which messages have been processed (acknowledged).                │
│                                                                            │
│ Key concepts:                                                              │
│   - Group: Named collection of consumers reading from a stream             │
│   - Consumer: Named client within a group                                  │
│   - PEL (Pending Entries List): Unacknowledged messages per consumer       │
│   - last_delivered_id: Tracks position in stream for the group             │
│                                                                            │
│ XGROUP CREATE key group id [MKSTREAM]  Create consumer group               │
│   Example: XGROUP CREATE mystream mygroup 0 MKSTREAM                       │
│   IDs: "0" (all messages), "$" (only new), specific ID                     │
│   MKSTREAM: Create stream if it doesn't exist                              │
│                                                                            │
│ XGROUP DESTROY key group              Delete consumer group                │
│   Example: XGROUP DESTROY mystream mygroup                                 │
│                                                                            │
│ XGROUP SETID key group id             Set group's last_delivered_id        │
│   Example: XGROUP SETID mystream mygroup 0   # Reprocess all messages      │
│                                                                            │
│ XGROUP DELCONSUMER key group consumer Remove consumer from group           │
│   Example: XGROUP DELCONSUMER mystream mygroup consumer1                   │
│                                                                            │
│ XREADGROUP GROUP group consumer [COUNT n] [BLOCK ms] STREAMS key id        │
│   Read messages for a consumer in a group                                  │
│   Example: XREADGROUP GROUP mygroup consumer1 STREAMS mystream >           │
│   Example: XREADGROUP GROUP mygroup consumer1 COUNT 10 STREAMS mystream >  │
│   Example: XREADGROUP GROUP mygroup consumer1 BLOCK 5000 STREAMS mystream >│
│   Special IDs:                                                             │
│     ">" : Only new messages never delivered to any consumer                │
│     "0" : Pending messages (delivered but not acknowledged)                │
│                                                                            │
│ XACK key group id [id ...]            Acknowledge message(s) as processed  │
│   Example: XACK mystream mygroup 1763006032172-0                           │
│   Example: XACK mystream mygroup 1763006032172-0 1763006032173-0           │
│   Returns: Number of messages successfully acknowledged                    │
│   Note: Removes messages from consumer's PEL                               │
│                                                                            │
│ XPENDING key group [start end count]  View pending (unacked) messages      │
│   Example: XPENDING mystream mygroup                    # Summary          │
│   Example: XPENDING mystream mygroup - + 10             # First 10 pending │
│   Example: XPENDING mystream mygroup - + 10 consumer1   # For consumer1    │
│                                                                            │
│ XCLAIM key group consumer min-idle-time id [id ...]                        │
│   Claim pending messages from another consumer                             │
│   Example: XCLAIM mystream mygroup consumer2 60000 1763006032172-0         │
│   Use when a consumer crashes and messages need reassignment               │
│                                                                            │
│ XAUTOCLAIM key group consumer min-idle-time start [COUNT n]                │
│   Auto-claim idle pending messages (Redis 6.2+)                            │
│   Example: XAUTOCLAIM mystream mygroup consumer2 60000 0-0 COUNT 10        │
│                                                                            │
│ XINFO GROUPS key                      List consumer groups                 │
│   Example: XINFO GROUPS mystream                                           │
│                                                                            │
│ XINFO CONSUMERS key group             List consumers in a group            │
│   Example: XINFO CONSUMERS mystream mygroup                                │
│                                                                            │
│ Real-world example workflow:                                               │
│   # Setup                                                                  │
│   XGROUP CREATE orders orderprocessors 0 MKSTREAM                          │
│                                                                            │
│   # Producer adds orders                                                   │
│   XADD orders * order_id "1001" product "laptop"                           │
│   XADD orders * order_id "1002" product "phone"                            │
│                                                                            │
│   # Consumer 1 reads and processes                                         │
│   XREADGROUP GROUP orderprocessors worker1 COUNT 1 STREAMS orders >        │
│   # ... process order 1001 ...                                             │
│   XACK orders orderprocessors 1763006032172-0                              │
│                                                                            │
│   # Consumer 2 reads next message                                          │
│   XREADGROUP GROUP orderprocessors worker2 COUNT 1 STREAMS orders >        │
│   # ... process order 1002 ...                                             │
│   XACK orders orderprocessors 1763006032173-0                              │
│                                                                            │
│   # Check pending messages                                                 │
│   XPENDING orders orderprocessors                                          │
│                                                                            │
│ Use cases:                                                                 │
│   - Distributed task processing (multiple workers)                         │
│   - Reliable message queues (at-least-once delivery)                       │
│   - Load balancing across consumers                                        │
│   - Fault-tolerant event processing                                        │
└────────────────────────────────────────────────────────────────────────────┘

EOF
}

# Check for --help flag
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
    exit 0
fi

# Connect to Redis
if [ -z "$REDIS_URL" ]; then
    echo "Error: REDIS_URL environment variable is not set"
    echo ""
    echo "Usage:"
    echo ""
    echo "  In your project root directory,"
    echo ""
    echo "  $ source .env.local.sh"
    echo "  $ ./scripts/redis.sh"
    echo ""
    echo "Or set manually:"
    echo ""
    echo "  $ export REDIS_URL='redis://localhost:6379'"
    echo "  $ ./scripts/redis.sh"
    echo ""
    echo "Or connect directly:"
    echo ""
    echo "  $ redis-cli -h localhost -p 6379"
    exit 1
fi

redis-cli -u "$REDIS_URL" 2>/dev/null || {
    echo "Error: Failed to connect to Redis using: redis-cli -u $REDIS_URL"
    echo ""
    echo "Possible solutions:"
    echo "  1. Check if REDIS_URL is correct: $REDIS_URL"
    echo "  2. Verify Redis server is running"
    echo "  3. Try connecting directly: redis-cli -h localhost -p 6379"
    echo "  4. Run './redis.sh --help' for more information"
    exit 1
}
