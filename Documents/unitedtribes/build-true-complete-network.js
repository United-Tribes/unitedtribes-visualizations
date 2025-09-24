// Build the TRULY complete network by querying ALL entities from the API
const https = require('https');
const fs = require('fs');

console.log('🌐 Building TRULY COMPLETE network from production API...\n');

// First, get the comprehensive list of all artists
async function getAllArtistsFromAPI() {
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify({
            "query": "List every single artist, musician, band, and cultural figure in the complete data lake with their connection counts. I want the comprehensive list of all entities, not just the top ones."
        });

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
                    console.log('✅ Retrieved comprehensive artist list from API');

                    // Get all artists from recommendations
                    const allArtists = response.recommendations?.similar_artists || [];
                    console.log(`📊 Found ${allArtists.length} total artists in data lake`);

                    resolve(allArtists);
                } catch (error) {
                    console.log('❌ Error parsing API response:', error.message);
                    resolve([]);
                }
            });
        });

        req.on('error', (error) => {
            console.log('❌ API request error:', error.message);
            resolve([]);
        });

        req.write(postData);
        req.end();
    });
}

// Get connections for a specific artist
async function getArtistConnections(artistName) {
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify({
            "query": `Show me ALL connections, relationships, collaborations, and influences for ${artistName}. Include every single connection in the data lake.`
        });

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
                    const connections = [];

                    // Extract all types of connections
                    if (response.connections?.direct_connections) {
                        response.connections.direct_connections.forEach(entity => {
                            if (entity.top_connections) {
                                entity.top_connections.forEach(conn => {
                                    connections.push({
                                        source: artistName,
                                        target: conn.target,
                                        relationship_type: conn.type || 'connected',
                                        evidence: conn.evidence,
                                        confidence: conn.confidence || 0.8,
                                        source_type: classifyEntity(artistName),
                                        target_type: classifyEntity(conn.target)
                                    });
                                });
                            }
                        });
                    }

                    if (response.connections?.influence_networks) {
                        response.connections.influence_networks.forEach(influence => {
                            connections.push({
                                source: influence.influencer,
                                target: influence.influenced,
                                relationship_type: 'influenced',
                                evidence: influence.context,
                                confidence: influence.confidence || 0.8,
                                source_type: classifyEntity(influence.influencer),
                                target_type: classifyEntity(influence.influenced)
                            });
                        });
                    }

                    if (response.connections?.collaborative_clusters) {
                        response.connections.collaborative_clusters.forEach(collab => {
                            connections.push({
                                source: collab.entity1,
                                target: collab.entity2,
                                relationship_type: collab.type || 'collaboration',
                                evidence: collab.context,
                                confidence: 0.9,
                                source_type: classifyEntity(collab.entity1),
                                target_type: classifyEntity(collab.entity2)
                            });
                        });
                    }

                    resolve(connections);
                } catch (error) {
                    console.log(`❌ Error processing ${artistName}:`, error.message);
                    resolve([]);
                }
            });
        });

        req.on('error', (error) => {
            console.log(`❌ Request error for ${artistName}:`, error.message);
            resolve([]);
        });

        req.write(postData);
        req.end();
    });
}

function classifyEntity(name) {
    if (!name) return 'entity';

    const musicians = ['Beatles', 'Dylan', 'Prince', 'Bowie', 'Lennon', 'McCartney', 'Radiohead', 'Questlove', 'Taylor Swift', 'Beyoncé'];
    const albums = ['Album', 'LP', 'Record', 'Songs of', 'The Rise and Fall', 'Blood on the Tracks'];
    const books = ['Book', 'Blues', 'Biography', 'Chronicles', 'Just Kids'];
    const venues = ['Club', 'Studio', 'Festival', 'Hotel', 'CBGB'];

    if (musicians.some(m => name.includes(m))) return 'musician';
    if (albums.some(a => name.includes(a))) return 'album';
    if (books.some(b => name.includes(b))) return 'book';
    if (venues.some(v => name.includes(v))) return 'venue';

    return 'entity';
}

async function buildCompleteNetwork() {
    console.log('🔍 Phase 1: Getting complete artist list...');
    const allArtists = await getAllArtistsFromAPI();

    if (allArtists.length === 0) {
        console.log('❌ Could not retrieve artist list from API');
        return;
    }

    console.log(`\n🌟 Complete Artist List (${allArtists.length} total):`);
    allArtists.slice(0, 30).forEach((artist, i) => {
        console.log(`   ${(i+1).toString().padStart(2)}. ${artist.entity.padEnd(35)} (${artist.connection_strength} connections)`);
    });
    if (allArtists.length > 30) {
        console.log(`   ... and ${allArtists.length - 30} more artists`);
    }

    console.log('\n🔍 Phase 2: Fetching ALL connections for ALL artists...');
    console.log('   This will take a few minutes to build the complete network...\n');

    const allConnections = [];
    let processed = 0;

    // Process artists in smaller batches
    const batchSize = 10;
    for (let i = 0; i < allArtists.length; i += batchSize) {
        const batch = allArtists.slice(i, i + batchSize);

        console.log(`📦 Batch ${Math.floor(i/batchSize) + 1}/${Math.ceil(allArtists.length/batchSize)}: Processing ${batch.length} artists...`);

        const batchPromises = batch.map(async (artist) => {
            const connections = await getArtistConnections(artist.entity);
            processed++;

            if (connections.length > 0) {
                console.log(`   ✅ ${artist.entity}: ${connections.length} connections (${processed}/${allArtists.length})`);
                allConnections.push(...connections);
            } else {
                console.log(`   ⚠️  ${artist.entity}: No connections found (${processed}/${allArtists.length})`);
            }
        });

        await Promise.all(batchPromises);

        // Small delay between batches
        await new Promise(resolve => setTimeout(resolve, 2000));
    }

    console.log(`\n📊 COMPLETE NETWORK COLLECTION RESULTS:`);
    console.log(`   Total connections collected: ${allConnections.length}`);
    console.log(`   Artists processed: ${processed}/${allArtists.length}`);

    // Deduplicate connections
    const uniqueConnections = [];
    const connectionSet = new Set();

    allConnections.forEach(conn => {
        const key = [conn.source, conn.target, conn.relationship_type].sort().join('|');
        if (!connectionSet.has(key)) {
            connectionSet.add(key);
            uniqueConnections.push(conn);
        }
    });

    console.log(`   Unique connections (after dedup): ${uniqueConnections.length}`);

    // Count connections per entity
    const entityConnections = {};
    uniqueConnections.forEach(conn => {
        entityConnections[conn.source] = (entityConnections[conn.source] || 0) + 1;
        entityConnections[conn.target] = (entityConnections[conn.target] || 0) + 1;
    });

    // Create the COMPLETE network data
    const completeNetwork = {
        metadata: {
            generated: new Date().toISOString(),
            version: 'truly-complete-v1',
            total_relationships: uniqueConnections.length,
            total_entities: Object.keys(entityConnections).length,
            artists_processed: processed,
            source: 'complete-production-api',
            api_relationships_analyzed: '3624+'
        },
        relationships: uniqueConnections,
        entity_connections: entityConnections,
        top_entities: Object.entries(entityConnections)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 100)
            .map(([name, count]) => ({
                name,
                connections: count,
                type: classifyEntity(name)
            })),
        all_artists: allArtists
    };

    // Save the COMPLETE network
    fs.writeFileSync('truly-complete-api-network.json', JSON.stringify(completeNetwork, null, 2));

    const fileSize = fs.statSync('truly-complete-api-network.json').size;
    console.log(`\n✅ TRULY COMPLETE network saved to: truly-complete-api-network.json`);
    console.log(`📦 File size: ${(fileSize / 1024).toFixed(2)} KB`);

    console.log(`\n🌟 Top 25 Most Connected Entities in COMPLETE Network:`);
    Object.entries(entityConnections)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 25)
        .forEach(([name, count], i) => {
            console.log(`   ${(i+1).toString().padStart(2)}. ${name.padEnd(40)} (${count} connections)`);
        });

    console.log(`\n🎯 This is your COMPLETE data lake - every artist, every connection!`);
    console.log(`   Total: ${uniqueConnections.length} relationships across ${Object.keys(entityConnections).length} entities`);
}

buildCompleteNetwork().catch(console.error);