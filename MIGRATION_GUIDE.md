# Migration Guide: Single Key to Multiple Keys Authentication

This guide helps you migrate from the old single magic key system to the new multiple keys system.

## Overview of Changes

### Old System (Removed)
- Single magic key stored in `chatFeatures` collection
- Document ID: `magic_key_config`
- Field: `magic_key`
- No ability to disable keys
- No per-user tracking

### New System (Current)
- Multiple keys stored in `userRegistrations` collection
- Each key is a separate document with `_id` = the key itself
- Keys can be enabled/disabled via `is_enabled` field
- Per-user tracking via optional `user` field
- Efficient lookups and management

## Quick Start Migration

### Step 1: Run the Migration Script

```bash
cd dbSetup
python migrate_keys_to_user_registrations.py --migrate
```

This will:
1. Find your existing key in `chatFeatures.magic_key_config`
2. Create a new document in `userRegistrations` with that key
3. Set `is_enabled: true` by default
4. Keep the old key in place for rollback safety

### Step 2: Verify the Migration

Check that your key was migrated:

```bash
python migrate_keys_to_user_registrations.py --list
```

You should see your key listed as enabled.

### Step 3: Test the New System

Test that authentication works with the migrated key:

```bash
cd ../src/api
python test_auth_integration.py
```

Or test via the API:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello",
    "magic_key": "your-migrated-key-here"
  }'
```

### Step 4: Clean Up Old System (Optional)

Once you've verified the new system works, you can remove the old configuration:

```bash
cd dbSetup
python migrate_keys_to_user_registrations.py --migrate --remove-old
```

This removes the `magic_key_config` document from the `chatFeatures` collection.

## Adding New Keys

After migration, you can add new keys for different users:

```bash
python migrate_keys_to_user_registrations.py \
  --add-key "user-2-key-xyz" \
  --notes "Key for User 2"
```

## Managing Keys

### Disable a Key

```bash
python migrate_keys_to_user_registrations.py --disable-key "old-key-123"
```

### Enable a Key

```bash
python migrate_keys_to_user_registrations.py --enable-key "old-key-123"
```

### List All Keys

```bash
python migrate_keys_to_user_registrations.py --list
```

## Rollback Plan

If you need to rollback to the old system:

1. The old `magic_key_config` document is preserved by default (unless you used `--remove-old`)
2. Revert the code changes to the previous version
3. Restart your application

## Troubleshooting

### "Key not found" errors after migration

Check if the key exists in the new collection:

```javascript
// MongoDB Shell
use your_database_name
db.userRegistrations.find().pretty()
```

### Migration script can't find old key

The old key might not exist. Create a new key manually:

```bash
python migrate_keys_to_user_registrations.py \
  --add-key "your-new-key-here" \
  --notes "Admin key"
```

### Frontend still using old key

The frontend doesn't need changes - it works with both systems. Just make sure:
1. The key is in localStorage or passed via URL
2. The key exists in the `userRegistrations` collection
3. The key has `is_enabled: true`

## Database Schema Comparison

### Old Schema (chatFeatures collection)

```javascript
{
  _id: "magic_key_config",
  magic_key: "single-shared-key-123"
}
```

### New Schema (userRegistrations collection)

```javascript
// Multiple documents, one per key
{
  _id: "user-1-key-abc",
  is_enabled: true,
  user: "user1@example.com",
  created_at: "2025-10-10T00:00:00Z",
  notes: "Key for User 1"
}

{
  _id: "user-2-key-def",
  is_enabled: false,
  user: "user2@example.com",
  created_at: "2025-10-09T00:00:00Z",
  disabled_at: "2025-10-10T12:00:00Z",
  notes: "Key for User 2 - disabled for security reasons"
}
```

## Code Changes Summary

### Backend Changes

**File: `src/api/routers/chat.py`**

The `validate_magic_key()` function was updated to:
- Query `userRegistrations` collection instead of `chatFeatures`
- Check the `is_enabled` field
- Use the key as the document `_id` for efficient lookups
- Provide backwards compatibility (defaults to enabled if field missing)

**Before:**
```python
config_collection = db["chatFeatures"]
config_doc = config_collection.find_one({"_id": "magic_key_config"})
valid_key = config_doc.get("magic_key")
is_valid = valid_key is not None and magic_key == valid_key
```

**After:**
```python
user_registrations_collection = db["userRegistrations"]
key_doc = user_registrations_collection.find_one({"_id": magic_key})
is_enabled = key_doc.get("is_enabled", True)
```

### Frontend Changes

**No changes required!** The frontend already supports magic keys and works with the new system.

## Benefits of the New System

1. **Multiple Users**: Each user can have their own unique key
2. **Fine-grained Control**: Disable individual keys without affecting others
3. **Better Tracking**: Associate keys with users for auditing
4. **Scalability**: Add unlimited keys without modifying configuration
5. **Security**: Easier to rotate keys and manage access
6. **Backwards Compatible**: Old keys continue to work if migrated

## Next Steps

After migration:

1. Generate unique keys for each user
2. Disable the original shared key
3. Distribute new keys to users
4. Monitor usage per key
5. Set up regular key rotation policy

## Support

For detailed documentation, see:
- [AUTHENTICATION.md](AUTHENTICATION.md) - Complete authentication system documentation
- [src/api/test_auth.py](src/api/test_auth.py) - Unit tests showing expected behavior
- [src/api/test_auth_integration.py](src/api/test_auth_integration.py) - Integration tests

For questions or issues, please open a GitHub issue.
