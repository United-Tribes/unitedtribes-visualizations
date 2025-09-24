// Quick comprehensive snapshot with key queries
const https = require('https');
const fs = require('fs');

console.log('⚡ Creating QUICK comprehensive snapshot...\n');

// Focused queries to capture maximum data efficiently
const quickQueries = [
    "Show me all artists with more than 10 connections and their networks",
    "List all major musical collaborations and influences across all genres",
    "Show all cultural connections between music, literature, and arts",
    "List all venue and location connections in the cultural network",
    "Show cross-generational influences from 1960s to present"
];

let snapshotData = [];

async function executeQuickQuery(query, index) {
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

        console.log(`🔍 Query ${index + 1}/${quickQueries.length}: "${query}"`);

        const req = https.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => {
                data += chunk;
            });
            res.on('end', () => {
                try {
                    const response = JSON.parse(data);
                    console.log(`✅ Query ${index + 1} completed`);

                    if (response.insights?.total_relationships_analyzed) {
                        console.log(`   Relationships analyzed: ${response.insights.total_relationships_analyzed}`);
                    }

                    snapshotData.push({
                        query_index: index,
                        query: query,
                        response: response
                    });

                    resolve();
                } catch (error) {
                    console.log(`❌ Query ${index + 1}: Error - ${error.message}`);
                    resolve();
                }
            });
        });

        req.on('error', (error) => {
            console.log(`❌ Query ${index + 1}: Request error - ${error.message}`);
            resolve();
        });

        req.setTimeout(45000, () => {
            console.log(`⏱️  Query ${index + 1}: Timeout`);
            req.destroy();
            resolve();
        });

        req.write(postData);
        req.end();
    });
}

async function createQuickSnapshot() {
    console.log(`🚀 Executing ${quickQueries.length} strategic queries...\n`);

    // Execute all queries sequentially
    for (let i = 0; i < quickQueries.length; i++) {
        await executeQuickQuery(quickQueries[i], i);

        // Small delay between queries
        if (i < quickQueries.length - 1) {
            console.log('   Waiting 2 seconds...\n');
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
    }

    console.log(`\n📊 QUICK SNAPSHOT COMPLETE - Processing data...`);

    // Extract all relationships from collected data
    const allRelationships = [];
    const allEntities = new Set();
    const entityConnections = {};

    snapshotData.forEach((queryData) => {
        const response = queryData.response;

        // Extract direct connections
        if (response.connections?.direct_connections) {
            response.connections.direct_connections.forEach(entity => {
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
                            target_type: classifyEntity(conn.target)
                        });
                        allEntities.add(conn.target);
                    });
                }
            });
        }

        // Extract influence networks
        if (response.connections?.influence_networks) {
            response.connections.influence_networks.forEach(influence => {
                allRelationships.push({
                    source: influence.influencer,
                    target: influence.influenced,
                    relationship_type: 'influenced',
                    evidence: influence.context,
                    confidence: influence.confidence || 0.8,
                    source_type: classifyEntity(influence.influencer),
                    target_type: classifyEntity(influence.influenced)
                });
                allEntities.add(influence.influencer);
                allEntities.add(influence.influenced);
            });
        }

        // Extract collaborations
        if (response.connections?.collaborative_clusters) {
            response.connections.collaborative_clusters.forEach(collab => {
                allRelationships.push({
                    source: collab.entity1,
                    target: collab.entity2,
                    relationship_type: collab.type || 'collaboration',
                    evidence: collab.context,
                    confidence: 0.9,
                    source_type: classifyEntity(collab.entity1),
                    target_type: classifyEntity(collab.entity2)
                });
                allEntities.add(collab.entity1);
                allEntities.add(collab.entity2);
            });
        }

        // Extract recommendations
        if (response.recommendations?.similar_artists) {
            response.recommendations.similar_artists.forEach(artist => {
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

    // Count connections
    uniqueRelationships.forEach(rel => {
        entityConnections[rel.source] = (entityConnections[rel.source] || 0) + 1;
        entityConnections[rel.target] = (entityConnections[rel.target] || 0) + 1;
    });

    // Create comprehensive snapshot
    const quickSnapshot = {
        metadata: {
            generated: new Date().toISOString(),
            version: 'quick-comprehensive-v1',
            total_relationships: uniqueRelationships.length,
            total_entities: allEntities.size,
            queries_executed: snapshotData.length,
            source: 'strategic-api-snapshot'
        },
        relationships: uniqueRelationships,
        entity_connections: entityConnections,
        top_entities: Object.entries(entityConnections)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 100)
            .map(([name, count]) => ({
                name,
                connections: count,
                type: classifyEntity(name)
            }))
    };

    // Save the snapshot
    fs.writeFileSync('quick-comprehensive-snapshot.json', JSON.stringify(quickSnapshot, null, 2));

    const fileSize = fs.statSync('quick-comprehensive-snapshot.json').size;
    console.log(`\n✅ COMPREHENSIVE SNAPSHOT saved to: quick-comprehensive-snapshot.json`);
    console.log(`📦 File size: ${(fileSize / 1024).toFixed(2)} KB`);
    console.log(`📊 Contains:`);
    console.log(`   - ${uniqueRelationships.length} unique relationships`);
    console.log(`   - ${allEntities.size} total entities`);

    console.log(`\n🌟 Top 25 Most Connected Entities:`);
    Object.entries(entityConnections)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 25)
        .forEach(([name, count], i) => {
            console.log(`   ${(i+1).toString().padStart(2)}. ${name.padEnd(35)} (${count} connections)`);
        });

    console.log(`\n🎯 This snapshot captures a comprehensive view of your data lake!`);
    return quickSnapshot;
}

function classifyEntity(name) {
    if (!name) return 'entity';

    const musicians = ['Beatles', 'Dylan', 'Prince', 'Bowie', 'Lennon', 'McCartney', 'Smith', 'Reed', 'Coltrane', 'Questlove', 'Taylor Swift'];
    const albums = ['Album', 'LP', 'Record', 'Songs of', 'Blood on the Tracks'];
    const books = ['Book', 'Biography', 'Chronicles', 'Just Kids'];
    const venues = ['Club', 'Studio', 'Festival', 'Hotel', 'CBGB'];

    if (musicians.some(m => name.includes(m))) return 'musician';
    if (albums.some(a => name.includes(a))) return 'album';
    if (books.some(b => name.includes(b))) return 'book';
    if (venues.some(v => name.includes(v))) return 'venue';

    return 'entity';
}

createQuickSnapshot().then(snapshot => {
    console.log('\n🚀 Ready to embed in HTML application!');
}).catch(console.error);