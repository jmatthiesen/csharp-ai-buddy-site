# Multiple API Key Authentication System

This document describes the multiple API key authentication system implemented for the C# AI Buddy application.

## Overview

The application now supports multiple API keys for authentication, allowing:
- One unique key per user
- Ability to disable keys without deletion
- Fine-grained access control
- Easy key management

## Database Schema

### userRegistrations Collection

Each API key is stored as a separate document in the `userRegistrations` collection:

```json
{
  "_id": "your-api-key-here",
  "is_enabled": true,
  "created_at": "2025-10-10T00:00:00Z",
  "notes": "Optional notes about this key"
}
```

**Fields:**
- `_id` (string, required): The API key itself (used as the document ID for efficient lookups)
- `is_enabled` (boolean, optional): Whether the key is active. Defaults to `true` if not present
- `created_at` (string, optional): ISO 8601 timestamp of when the key was created
- `notes` (string, optional): Any additional notes about the key
- `disabled_at` (string, optional): ISO 8601 timestamp of when the key was disabled

## Implementation Details

### Backend Validation

The `validate_magic_key()` function in `src/api/routers/chat.py` performs the following steps:

1. Connects to MongoDB using environment variables `MONGODB_URI` and `DATABASE_NAME`
2. Queries the `userRegistrations` collection for a document with `_id` matching the provided key
3. Checks if the key exists
4. Checks if the `is_enabled` field is `true` (defaults to `true` if field is missing)
5. Returns `true` if key is valid and enabled, `false` otherwise

### Frontend Integration

The frontend (JavaScript) already supports magic keys and requires no changes. The keys are:
- Passed via URL parameter `?key=your-api-key`
- Stored in localStorage with 10-day expiration
- Sent in the `magic_key` field of API requests

### Development Environment

In development mode (`ENVIRONMENT=development`), magic key validation is skipped entirely for ease of development.

## Security Considerations

1. **Key Storage**: Keys are stored as document IDs for efficient lookups, but should still be treated as secrets
2. **HTTPS**: Always use HTTPS in production to prevent key interception
3. **Key Rotation**: Disable old keys and issue new ones periodically
4. **Monitoring**: Monitor for unusual patterns or unauthorized access attempts
5. **Rate Limiting**: Consider implementing rate limiting per key

## Testing

Unit tests are provided in `src/api/test_auth.py`:

```bash
cd src/api
python -m pytest test_auth.py -v
```

Tests cover:
- Valid enabled keys
- Valid disabled keys
- Non-existent keys
- Error handling
- Multiple keys scenarios

## Example Usage

### Manual Database Setup

You can also manually add keys using MongoDB tools:

```javascript
// MongoDB Shell
db.userRegistrations.insertOne({
  _id: "my-secure-api-key-123",
  is_enabled: true,
  user: "developer@example.com",
  created_at: new Date().toISOString(),
  notes: "Development key"
});
```

### Disable a Key via MongoDB

```javascript
// MongoDB Shell
db.userRegistrations.updateOne(
  { _id: "my-secure-api-key-123" },
  { 
    $set: { 
      is_enabled: false,
      disabled_at: new Date().toISOString()
    }
  }
);
```

### Delete a Key

```javascript
// MongoDB Shell
db.userRegistrations.deleteOne({ _id: "my-secure-api-key-123" });
```

## API Endpoint Behavior

### Chat Endpoint (`/api/chat`)

**With Valid Key:**
- Returns streaming response with AI chat content

**With Disabled Key:**
- HTTP 403 Forbidden
- Error message: "Invalid magic key. Please check your key and try again."

**With Missing Key (Production):**
- HTTP 401 Unauthorized
- Error message: "Magic key required for early access. Please provide a valid magic key."

**With No Key (Development):**
- Validation skipped, request proceeds normally

## Troubleshooting

### "Invalid magic key" Error

1. Check if the key is enabled:
   ```javascript
   db.userRegistrations.findOne({ _id: "your-key-here" })
   ```

2. Ensure environment variables are set correctly:
   - `MONGODB_URI`
   - `DATABASE_NAME`
   - `ENVIRONMENT` (should not be "development" in production)

## Best Practices

1. **Key Generation**: Use cryptographically secure random strings for keys (e.g., UUID v4, secure random bytes)
2. **Key Length**: Use keys of at least 32 characters
3. **Audit Trail**: Keep track of when keys are created, disabled, or deleted
4. **Regular Review**: Periodically review and clean up unused or old keys
5. **Documentation**: Document the purpose of each key in the `notes` field

## Future Enhancements

Potential improvements to consider:

- Key expiration dates
- Usage analytics per key
- Rate limiting per key
- Key rotation policies
- Admin UI for key management
- Webhooks for key events
- API endpoints for key management
