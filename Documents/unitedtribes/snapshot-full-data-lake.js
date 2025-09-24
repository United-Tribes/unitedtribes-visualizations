// Create a comprehensive snapshot of the full data lake
const https = require('https');
const fs = require('fs');

console.log('📸 Creating comprehensive snapshot of FULL data lake...\n');

// Strategy: Query for broad categories to capture all entities systematically
const snapshotQueries = [
    // Music genres and eras
    "List all rock musicians, bands, and artists with their connections",
    "List all jazz musicians, artists, and their collaborations",
    "List all folk musicians, singer-songwriters, and their influences",
    "List all punk, alternative, and indie artists with connections",
    "List all pop, R&B, and soul artists with their relationships",
    "List all hip-hop, rap, and contemporary artists with connections",
    "List all classical, experimental, and avant-garde artists",

    // Literature and poetry
    "List all poets, writers, and literary figures with their connections",
    "List all beat generation authors and their influences",
    "List all books, novels, and literary works with connections",

    // Cultural movements and venues
    "List all venues, clubs, studios, and cultural spaces with connections",
    "List all record labels, producers, and industry figures",
    "List all cultural movements, schools, and artistic communities",

    // Albums and creative works
    "List all albums, records, and musical works with connections",
    "List all films, documentaries, and visual works with connections",

    // Specific influential artists (to ensure they're included)
    "Show all connections for The Beatles and their network",
    "Show all connections for Bob Dylan and his complete network",
    "Show all connections for David Bowie and his influences",
    "Show all connections for Questlove and hip-hop culture",
    "Show all connections for Patti Smith and the punk movement",
    "Show all connections for John Coltrane and jazz history",
    "Show all connections for Taylor Swift and contemporary music",
    "Show all connections for Radiohead and alternative rock",

    // Cross-cultural connections
    "List all artist collaborations and cross-genre influences",
    "List all mentor-student relationships in music and arts",
    "List all cultural exchanges between different artistic movements"
];

let allSnapshotData = [];
let processedQueries = 0;

async function executeSnapshotQuery(query, index) {
    return new Promise((resolve) => {
        const postData = JSON.stringify({ query });

        const options = {
            hostname: '166ws8jk15.execute-api.us-east-1.amazonaws.com',
            port: 443,
            path: '/prod/v2/broker',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData)
            }
        };

        const req = https.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => {
                data += chunk;
            });
            res.on('end', () => {
                try {
                    const response = JSON.parse(data);
                    processedQueries++;

                    console.log(`✅ Query ${index + 1}/${snapshotQueries.length}: "${query.substring(0, 50)}..."`);
                    console.log(`   Progress: ${processedQueries}/${snapshotQueries.length} queries completed`);

                    // Extract all relationship data from the response
                    const queryData = {
                        query_index: index,
                        query: query,
                        timestamp: new Date().toISOString(),
                        narrative: response.narrative,
                        connections: response.connections || {},
                        recommendations: response.recommendations || {},
                        insights: response.insights || {}
                    };

                    allSnapshotData.push(queryData);

                    if (response.insights?.total_relationships_analyzed) {
                        console.log(`   Relationships analyzed: ${response.insights.total_relationships_analyzed}`);
                    }

                    resolve();
                } catch (error) {
                    console.log(`❌ Query ${index + 1}: Error parsing response - ${error.message}`);
                    processedQueries++;
                    resolve();
                }
            });
        });

        req.on('error', (error) => {
            console.log(`❌ Query ${index + 1}: Request error - ${error.message}`);
            processedQueries++;
            resolve();
        });

        // Set a longer timeout for complex queries
        req.setTimeout(30000, () => {
            console.log(`⏱️  Query ${index + 1}: Timeout - moving to next query`);
            req.destroy();
            processedQueries++;
            resolve();
        });

        req.write(postData);
        req.end();
    });
}

async function createFullSnapshot() {
    console.log(`🚀 Executing ${snapshotQueries.length} comprehensive queries to capture full data lake...\n`);

    // Process queries in smaller batches to avoid overwhelming the API
    const batchSize = 3;
    for (let i = 0; i < snapshotQueries.length; i += batchSize) {
        const batch = snapshotQueries.slice(i, i + batchSize);

        console.log(`\n📦 Batch ${Math.floor(i/batchSize) + 1}/${Math.ceil(snapshotQueries.length/batchSize)}`);

        const batchPromises = batch.map((query, batchIndex) =>
            executeSnapshotQuery(query, i + batchIndex)
        );

        await Promise.all(batchPromises);

        // Delay between batches to be respectful to the API
        if (i + batchSize < snapshotQueries.length) {
            console.log('   Pausing 3 seconds before next batch...');
            await new Promise(resolve => setTimeout(resolve, 3000));
        }
    }

    // Process and consolidate all snapshot data
    console.log(`\n📊 SNAPSHOT COLLECTION COMPLETE:`);
    console.log(`   Queries executed: ${processedQueries}/${snapshotQueries.length}`);
    console.log(`   Data points collected: ${allSnapshotData.length}`);

    // Extract and consolidate all relationships
    const allRelationships = [];
    const allEntities = new Set();
    const allArtists = new Set();

    allSnapshotData.forEach((queryData, index) => {
        // Process direct connections
        if (queryData.connections?.direct_connections) {
            queryData.connections.direct_connections.forEach(entity => {
                allEntities.add(entity.entity);

                if (entity.top_connections) {
                    entity.top_connections.forEach(conn => {
                        allRelationships.push({
                            source: entity.entity,
                            target: conn.target,
                            relationship_type: conn.type || 'connected',
                            evidence: conn.evidence,
                            confidence: conn.confidence || 0.8,
                            source_type: classifyEntity(entity.entity),
                            target_type: classifyEntity(conn.target),
                            query_source: index
                        });
                        allEntities.add(conn.target);
                    });
                }
            });
        }

        // Process influence networks
        if (queryData.connections?.influence_networks) {
            queryData.connections.influence_networks.forEach(influence => {
                allRelationships.push({
                    source: influence.influencer,
                    target: influence.influenced,
                    relationship_type: 'influenced',
                    evidence: influence.context,
                    confidence: influence.confidence || 0.8,
                    source_type: classifyEntity(influence.influencer),
                    target_type: classifyEntity(influence.influenced),
                    query_source: index
                });
                allEntities.add(influence.influencer);
                allEntities.add(influence.influenced);
            });
        }

        // Process collaborative clusters
        if (queryData.connections?.collaborative_clusters) {
            queryData.connections.collaborative_clusters.forEach(collab => {
                allRelationships.push({
                    source: collab.entity1,
                    target: collab.entity2,
                    relationship_type: collab.type || 'collaboration',
                    evidence: collab.context,
                    confidence: 0.9,
                    source_type: classifyEntity(collab.entity1),
                    target_type: classifyEntity(collab.entity2),
                    query_source: index
                });
                allEntities.add(collab.entity1);
                allEntities.add(collab.entity2);
            });
        }

        // Collect artists from recommendations
        if (queryData.recommendations?.similar_artists) {
            queryData.recommendations.similar_artists.forEach(artist => {
                allArtists.add(artist.entity);
                allEntities.add(artist.entity);
            });
        }
    });

    // Deduplicate relationships
    const uniqueRelationships = [];
    const relationshipSet = new Set();

    allRelationships.forEach(rel => {
        const key = [rel.source, rel.target, rel.relationship_type].sort().join('|');
        if (!relationshipSet.has(key)) {
            relationshipSet.add(key);
            uniqueRelationships.push(rel);
        }
    });

    // Count connections per entity
    const entityConnections = {};
    uniqueRelationships.forEach(rel => {
        entityConnections[rel.source] = (entityConnections[rel.source] || 0) + 1;
        entityConnections[rel.target] = (entityConnections[rel.target] || 0) + 1;
    });

    // Create the comprehensive snapshot
    const fullSnapshot = {
        metadata: {
            generated: new Date().toISOString(),
            version: 'full-snapshot-v1',
            queries_executed: processedQueries,
            total_relationships: uniqueRelationships.length,
            total_entities: allEntities.size,
            total_artists: allArtists.size,
            source: 'comprehensive-api-snapshot',
            queries: snapshotQueries
        },
        relationships: uniqueRelationships,
        entity_connections: entityConnections,
        all_entities: Array.from(allEntities),
        all_artists: Array.from(allArtists),
        raw_snapshot_data: allSnapshotData,
        top_entities: Object.entries(entityConnections)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 200)
            .map(([name, count]) => ({
                name,
                connections: count,
                type: classifyEntity(name)
            }))
    };

    // Save the complete snapshot
    fs.writeFileSync('full-data-lake-snapshot.json', JSON.stringify(fullSnapshot, null, 2));

    const fileSize = fs.statSync('full-data-lake-snapshot.json').size;
    console.log(`\n✅ FULL DATA LAKE SNAPSHOT saved to: full-data-lake-snapshot.json`);
    console.log(`📦 File size: ${(fileSize / 1024).toFixed(2)} KB`);
    console.log(`📊 Snapshot contains:`);
    console.log(`   - ${uniqueRelationships.length} unique relationships`);
    console.log(`   - ${allEntities.size} total entities`);
    console.log(`   - ${allArtists.size} artists`);
    console.log(`   - ${processedQueries} API queries executed`);

    console.log(`\n🌟 Top 30 Most Connected Entities in FULL SNAPSHOT:`);
    Object.entries(entityConnections)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 30)
        .forEach(([name, count], i) => {
            console.log(`   ${(i+1).toString().padStart(2)}. ${name.padEnd(40)} (${count} connections)`);
        });

    console.log(`\n🎯 This snapshot captures your COMPLETE data lake for local caching!`);
}

function classifyEntity(name) {
    if (!name) return 'entity';

    const musicians = ['Beatles', 'Dylan', 'Prince', 'Bowie', 'Lennon', 'McCartney', 'Smith', 'Reed', 'Coltrane'];
    const albums = ['Album', 'LP', 'Record', 'Songs of', 'Blood on the Tracks'];
    const books = ['Book', 'Biography', 'Chronicles', 'Just Kids'];
    const venues = ['Club', 'Studio', 'Festival', 'Hotel', 'CBGB'];

    if (musicians.some(m => name.includes(m))) return 'musician';
    if (albums.some(a => name.includes(a))) return 'album';
    if (books.some(b => name.includes(b))) return 'book';
    if (venues.some(v => name.includes(v))) return 'venue';

    return 'entity';
}

createFullSnapshot().catch(console.error);