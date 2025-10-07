# Samples Gallery Setup and Usage

This document explains how to set up and use the samples gallery feature that was added to the C# AI Buddy website.

## 🚀 Quick Start

### Prerequisites
- MongoDB database (local or cloud)
- Python 3.8+ with required packages installed
- Environment variables configured

### Environment Setup

1. **Install API Dependencies**:
   ```bash
   cd src/api
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**:
   Create a `.env` file in the `src/api` directory:
   ```env
   # OpenAI API Configuration
   OPENAI_API_KEY=your_openai_api_key_here
   
   # MongoDB Configuration for Knowledge Base and Samples
   MONGODB_URI=mongodb://your_mongodb_connection_string_here
   DATABASE_NAME=your_database_name_here
   
   # Optional: Port for the API server (defaults to 8000)
   PORT=8000
   
   # Optional: Environment (development, production)
   ENVIRONMENT=development
   
   # Optional: OpenTelemetry endpoint for telemetry data
   OTEL_EXPORTER_OTLP_ENDPOINT=your_otel_endpoint_here
   ```

3. **Populate Sample Data**:
   ```bash
   cd src/api
   python sample_data.py
   ```

4. **Start the Backend API**:
   ```bash
   cd src/api
   python main.py
   ```

5. **Start the Frontend** (in a new terminal):
   ```bash
   cd src/frontend
   python -m http.server 3000
   ```

6. **Open in Browser**:
   - Chat Interface: http://localhost:3000
   - Sample Gallery: http://localhost:3000?tab=samples

## 📊 API Endpoints

### Samples API
- `GET /api/samples` - Get paginated samples with search and filtering
  - Query parameters:
    - `page` (int): Page number (default: 1)
    - `page_size` (int): Results per page (default: 20, max: 100)
    - `search` (string): Search query for title, description, author, or tags
    - `tags` (string): Comma-separated list of tags to filter by

- `GET /api/samples/{sample_id}` - Get individual sample details
- `GET /api/samples/tags` - Get all available tags
- `POST /api/telemetry` - Record telemetry events

### Example API Calls
```bash
# Get all samples
curl http://localhost:8000/api/samples

# Search for samples
curl "http://localhost:8000/api/samples?search=blazor"

# Filter by tags
curl "http://localhost:8000/api/samples?tags=msft,blazor"

# Get sample details
curl http://localhost:8000/api/samples/sample-id-here

# Get available tags
curl http://localhost:8000/api/samples/tags
```

## 🎨 Frontend Features

### Navigation
- **Tab Switching**: Click "AI Chat" or "Sample Gallery" tabs
- **Deep Linking**: Share URLs like `?tab=samples` to link directly to the gallery

### Search & Filtering
- **Real-time Search**: Type in the search box to filter samples
- **Tag Filters**: Click "Filters" button to see and select tag filters
- **Combined Search**: Use both search and tag filters together
- **Clear Filters**: Use "Clear All" button to reset all filters

### Sample Cards
- **Sample Info**: Title, author, truncated description, and tags
- **Click to View**: Click any card to open the detailed modal

### Sample Details Modal
- **Full Information**: Complete description, author links, source links
- **Git Instructions**: Ready-to-copy `git clone` commands
- **External Link Tracking**: Tracks clicks to GitHub repositories

### Telemetry Features
- **Toggle Control**: Click "Telemetry: On/Off" button to control tracking
- **Persistent Setting**: Preference saved in browser localStorage
- **Events Tracked**:
  - Filter usage (which tags are selected)
  - Sample views (which samples are opened)
  - External link clicks (GitHub repository visits)
  - No-results searches (queries that return no matches)

## 🗄️ Database Schema

### Samples Collection
Each sample document follows this structure:
```json
{
  "id": "unique-sample-id",
  "title": "Sample Title",
  "description": "Full description of the sample project...",
  "preview": "path/to/preview/image.png",
  "authorUrl": "https://github.com/author",
  "author": "Author Name",
  "source": "https://github.com/author/repo",
  "tags": ["tag1", "tag2", "msft"]
}
```

**Note**: The `msft` tag is special and triggers the Microsoft badge display.

## 🔧 Development

### Adding New Samples
1. **Via Script**: Add to the `SAMPLE_DATA` array in `sample_data.py` and run the script
2. **Via API**: Use MongoDB tools to insert documents directly
3. **Via Database**: Use MongoDB Compass or similar tools

### Customizing the UI
- **Styles**: Edit `src/frontend/styles.css`
- **Layout**: Modify `src/frontend/index.html`
- **Behavior**: Update `src/frontend/script.js`

### Telemetry Integration
The app uses OpenTelemetry for observability:
- **Traces**: API requests and database operations
- **Custom Events**: User interactions and search patterns
- **Configuration**: Set `OTEL_EXPORTER_OTLP_ENDPOINT` in environment

## 🐛 Troubleshooting

### Common Issues

1. **"Database not configured" Error**:
   - Check that `MONGODB_URI` and `DATABASE_NAME` are set in `.env`
   - Verify MongoDB is running and accessible

2. **No samples showing**:
   - Run `python sample_data.py` to populate test data
   - Check MongoDB connection and collection name

3. **Search not working**:
   - Ensure JavaScript is enabled in browser
   - Check browser console for errors

4. **Telemetry not tracking**:
   - Verify telemetry is enabled (toggle button shows "On")
   - Check that `OTEL_EXPORTER_OTLP_ENDPOINT` is configured (optional)

### Debug Mode
Set `ENVIRONMENT=development` in `.env` to enable additional logging.

## 🔄 Production Deployment

### Environment Variables for Production
- Set `ENVIRONMENT=production`
- Use secure MongoDB connection strings
- Configure proper CORS origins in `main.py`
- Set up proper OpenTelemetry endpoint for monitoring

### Security Considerations
- Use HTTPS in production
- Implement proper authentication if needed
- Sanitize user input (already implemented in frontend)
- Monitor API rate limiting

## 📝 Sample Data

The `sample_data.py` script includes 20+ realistic sample projects covering:
- ✅ Microsoft-authored samples (with `msft` tag)
- ✅ Community samples
- ✅ Various technologies (.NET, Blazor, MAUI, ML.NET, etc.)
- ✅ Different complexity levels
- ✅ Real GitHub repository URLs

Run the script anytime to refresh the sample data or add new samples to the database.