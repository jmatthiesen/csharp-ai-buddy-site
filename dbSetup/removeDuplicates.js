/**
 * MongoDB Duplicate Document Removal Script
 * 
 * This script finds and removes duplicate documents in the MongoDB csharpAIBuddy database:
 * - Duplicates in the documents collection are detected based on sourceUrl
 * - Duplicates in document_chunks are based on source_url and content
 * 
 * The script will:
 * 1. Identify all duplicate records
 * 2. Keep the most recently indexed record (latest indexedDate/indexed_date)
 * 3. Delete the duplicate records
 * 
 * Usage:
 *   mongosh "mongodb://connection-string" --file remove_duplicates.js
 *   
 * Options (set at top of script):
 *   - DRY_RUN: Set to true to only show what would be deleted (default: true)
 *   - VERBOSE: Set to true for detailed output (default: false)
 *   - BATCH_SIZE: Number of records to process at once (default: 100)
 */

// Configuration - Modify these as needed
const DRY_RUN = true;  // Set to false to actually delete duplicates
const VERBOSE = false; // Set to true for detailed output
const BATCH_SIZE = 100;

// Database and collection names
const DATABASE_NAME = 'csharpAIBuddy';
const DOCUMENTS_COLLECTION = 'documents';
const CHUNKS_COLLECTION = 'document_chunks';
const cluster = Mongo("<connectionString>"); // Replace <connectionString> with your MongoDB connection string
const db = cluster.getDB(DATABASE_NAME);

// Statistics tracking
let stats = {
    documentsTotal: 0,
    documentsDuplicatesFound: 0,
    documentsDuplicatesDeleted: 0,
    chunksTotal: 0,
    chunksDuplicatesFound: 0,
    chunksDuplicatesDeleted: 0
};

/**
 * Print formatted messages with timestamps
 */
function logInfo(message) {
    print(`[${new Date().toISOString()}] INFO: ${message}`);
}

function logWarning(message) {
    print(`[${new Date().toISOString()}] WARNING: ${message}`);
}

function logError(message) {
    print(`[${new Date().toISOString()}] ERROR: ${message}`);
}

function logVerbose(message) {
    if (VERBOSE) {
        print(`[${new Date().toISOString()}] VERBOSE: ${message}`);
    }
}

/**
 * Get the most recent date from a document/chunk, handling null values
 */
function getMostRecentDate(item, dateField) {
    let date = item[dateField];
    if (!date && dateField === 'indexedDate') {
        date = item.createdDate;
    }
    if (!date && dateField === 'indexed_date') {
        date = item.created_date;
    }
    return date || new Date(0); // Return epoch if no date found
}

/**
 * Find duplicate documents based on sourceUrl
 */
function findDuplicateDocuments() {
    logInfo("Finding duplicate documents based on sourceUrl...");
    const collection = db.getCollection(DOCUMENTS_COLLECTION);
    
    // Get total document count
    stats.documentsTotal = collection.countDocuments({});
    logInfo(`Total documents in collection: ${stats.documentsTotal}`);
    
    // Aggregation pipeline to find duplicates
    const pipeline = [
        {
            $group: {
                _id: "$sourceUrl",
                count: { $sum: 1 },
                documents: {
                    $push: {
                        id: "$_id",
                        documentId: "$documentId",
                        title: "$title",
                        sourceUrl: "$sourceUrl",
                        indexedDate: "$indexedDate",
                        createdDate: "$createdDate"
                    }
                }
            }
        },
        {
            $match: {
                count: { $gt: 1 },
                _id: { $ne: null } // Exclude null sourceUrl values
            }
        }
    ];
    
    const duplicates = collection.aggregate(pipeline).toArray();
    
    logInfo(`Found ${duplicates.length} sourceUrl values with duplicates`);
    
    let totalDuplicatesToRemove = 0;
    duplicates.forEach(group => {
        totalDuplicatesToRemove += group.count - 1; // All but one are duplicates
        logVerbose(`sourceUrl: ${group._id} has ${group.count} duplicates`);
    });
    
    stats.documentsDuplicatesFound = totalDuplicatesToRemove;
    logInfo(`Total duplicate documents to remove: ${totalDuplicatesToRemove}`);
    
    return duplicates;
}

/**
 * Find duplicate chunks based on source_url and content
 */
function findDuplicateChunks() {
    logInfo("Finding duplicate chunks based on source_url and content...");
    const collection = db.getCollection(CHUNKS_COLLECTION);
    
    // Get total chunk count
    stats.chunksTotal = collection.countDocuments({});
    logInfo(`Total chunks in collection: ${stats.chunksTotal}`);
    
    // Aggregation pipeline to find duplicates
    const pipeline = [
        {
            $group: {
                _id: {
                    source_url: "$source_url",
                    content: "$content"
                },
                count: { $sum: 1 },
                chunks: {
                    $push: {
                        id: "$_id",
                        chunk_id: "$chunk_id",
                        source_url: "$source_url",
                        content_preview: { $substrCP: ["$content", 0, 100] },
                        indexed_date: "$indexed_date",
                        created_date: "$created_date",
                        chunk_index: "$chunk_index"
                    }
                }
            }
        },
        {
            $match: {
                count: { $gt: 1 },
                "_id.source_url": { $ne: null },
                "_id.content": { $ne: null }
            }
        }
    ];
    
    const duplicates = collection.aggregate(pipeline).toArray();
    
    logInfo(`Found ${duplicates.length} (source_url, content) combinations with duplicates`);
    
    let totalDuplicatesToRemove = 0;
    duplicates.forEach(group => {
        totalDuplicatesToRemove += group.count - 1; // All but one are duplicates
        logVerbose(`source_url: ${group._id.source_url} has ${group.count} duplicate chunks`);
    });
    
    stats.chunksDuplicatesFound = totalDuplicatesToRemove;
    logInfo(`Total duplicate chunks to remove: ${totalDuplicatesToRemove}`);
    
    return duplicates;
}

/**
 * Remove duplicate documents, keeping the most recent one
 */
function removeDuplicateDocuments(duplicates) {
    if (!duplicates || duplicates.length === 0) {
        logInfo("No duplicate documents to remove");
        return 0;
    }
    
    const collection = db.getCollection(DOCUMENTS_COLLECTION);
    let deletedCount = 0;
    
    duplicates.forEach(group => {
        if (group.count <= 1) return;
        
        const documents = group.documents;
        const sourceUrl = group._id;
        
        // Sort by indexedDate (most recent first), handling null values
        documents.sort((a, b) => {
            const dateA = getMostRecentDate(a, 'indexedDate');
            const dateB = getMostRecentDate(b, 'indexedDate');
            return new Date(dateB) - new Date(dateA);
        });
        
        // Keep the first one (most recent), delete the rest
        const keepDoc = documents[0];
        const deleteIds = documents.slice(1).map(doc => doc.id);
        
        logInfo(`Processing sourceUrl: ${sourceUrl}`);
        logInfo(`  Keeping document ID: ${keepDoc.id} (IndexedDate: ${keepDoc.indexedDate || 'N/A'})`);
        logInfo(`  Deleting ${deleteIds.length} duplicate document(s)`);
        
        if (VERBOSE) {
            documents.slice(1).forEach(doc => {
                logVerbose(`    Deleting: ${doc.id} (IndexedDate: ${doc.indexedDate || 'N/A'})`);
            });
        }
        
        if (!DRY_RUN) {
            try {
                const result = collection.deleteMany({ _id: { $in: deleteIds } });
                deletedCount += result.deletedCount;
                logInfo(`  Successfully deleted ${result.deletedCount} documents`);
            } catch (error) {
                logError(`  Error deleting documents: ${error}`);
            }
        } else {
            deletedCount += deleteIds.length;
            logInfo(`  [DRY RUN] Would delete ${deleteIds.length} documents`);
        }
    });
    
    return deletedCount;
}

/**
 * Remove duplicate chunks, keeping the most recent one
 */
function removeDuplicateChunks(duplicates) {
    if (!duplicates || duplicates.length === 0) {
        logInfo("No duplicate chunks to remove");
        return 0;
    }

    const collection = db.getCollection(CHUNKS_COLLECTION);
    let deletedCount = 0;
    
    duplicates.forEach(group => {
        if (group.count <= 1) return;
        
        const chunks = group.chunks;
        const sourceUrl = group._id.source_url;
        const contentPreview = group._id.content.substring(0, 50) + "...";
        
        // Sort by indexed_date (most recent first), handling null values
        chunks.sort((a, b) => {
            const dateA = getMostRecentDate(a, 'indexed_date');
            const dateB = getMostRecentDate(b, 'indexed_date');
            return new Date(dateB) - new Date(dateA);
        });
        
        // Keep the first one (most recent), delete the rest
        const keepChunk = chunks[0];
        const deleteIds = chunks.slice(1).map(chunk => chunk.id);
        
        logInfo(`Processing source_url: ${sourceUrl}`);
        logInfo(`  Content preview: ${contentPreview}`);
        logInfo(`  Keeping chunk ID: ${keepChunk.id} (IndexedDate: ${keepChunk.indexed_date || 'N/A'})`);
        logInfo(`  Deleting ${deleteIds.length} duplicate chunk(s)`);
        
        if (VERBOSE) {
            chunks.slice(1).forEach(chunk => {
                logVerbose(`    Deleting: ${chunk.id} (IndexedDate: ${chunk.indexed_date || 'N/A'})`);
            });
        }
        
        if (!DRY_RUN) {
            // try {
            //     const result = collection.deleteMany({ _id: { $in: deleteIds } });
            //     deletedCount += result.deletedCount;
            //     logInfo(`  Successfully deleted ${result.deletedCount} chunks`);
            // } catch (error) {
            //     logError(`  Error deleting chunks: ${error}`);
            // }
        } else {
            deletedCount += deleteIds.length;
            logInfo(`  [DRY RUN] Would delete ${deleteIds.length} chunks`);
        }
    });
    
    return deletedCount;
}

/**
 * Main execution function
 */
function main() {
    print("=".repeat(60));
    print("MongoDB Duplicate Document Removal");
    print("=".repeat(60));
    print(`Database: ${DATABASE_NAME}`);
    print(`Documents Collection: ${DOCUMENTS_COLLECTION}`);
    print(`Chunks Collection: ${CHUNKS_COLLECTION}`);
    print(`Mode: ${DRY_RUN ? 'DRY RUN' : 'EXECUTE DELETES'}`);
    print("=".repeat(60));
    
    try {
        // Test database connection
        print(db.getCollection(DOCUMENTS_COLLECTION).countDocuments({}));

        // Check if collections exist
        if (!db.getCollection(DOCUMENTS_COLLECTION)) {
            logWarning(`Documents collection '${DOCUMENTS_COLLECTION}' not found`);
        }
        if (!db.getCollection(CHUNKS_COLLECTION)) {
            logWarning(`Chunks collection '${CHUNKS_COLLECTION}' not found`);
        }
        
        // Process documents collection
        print("\n" + "=".repeat(40));
        print("PROCESSING DOCUMENTS COLLECTION");
        print("=".repeat(40));
        
        const duplicateDocs = findDuplicateDocuments();
        if (duplicateDocs.length > 0) {
            const deletedDocs = removeDuplicateDocuments(duplicateDocs);
            stats.documentsDuplicatesDeleted = deletedDocs;
        }
        
        // Process chunks collection
        print("\n" + "=".repeat(40));
        print("PROCESSING DOCUMENT_CHUNKS COLLECTION");
        print("=".repeat(40));
        
        const duplicateChunks = findDuplicateChunks();
        if (duplicateChunks.length > 0) {
            const deletedChunks = removeDuplicateChunks(duplicateChunks);
            stats.chunksDuplicatesDeleted = deletedChunks;
        }
        
        // Final summary
        print("\n" + "=".repeat(60));
        print("SUMMARY");
        print("=".repeat(60));
        print(`Documents Collection:`);
        print(`  Total documents: ${stats.documentsTotal}`);
        print(`  Duplicates found: ${stats.documentsDuplicatesFound}`);
        print(`  Duplicates ${DRY_RUN ? 'would be deleted' : 'deleted'}: ${stats.documentsDuplicatesDeleted}`);
        
        print(`\nChunks Collection:`);
        print(`  Total chunks: ${stats.chunksTotal}`);
        print(`  Duplicates found: ${stats.chunksDuplicatesFound}`);
        print(`  Duplicates ${DRY_RUN ? 'would be deleted' : 'deleted'}: ${stats.chunksDuplicatesDeleted}`);
        
        if (DRY_RUN) {
            print(`\n⚠️  This was a DRY RUN. No actual deletions were performed.`);
            print(`   Edit the script and set DRY_RUN = false to perform actual deletions.`);
        } else {
            print(`\n✅ Duplicate removal completed successfully.`);
        }
        
    } catch (error) {
        logError(`Unexpected error: ${error}`);
        throw error;
    }
}

// Execute the main function
main();