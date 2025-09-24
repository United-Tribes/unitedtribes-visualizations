// Script to fetch the complete data lake from the production API
const https = require('https');

console.log('🔍 Fetching complete data lake from production API...\n');

// List of major artists to query for comprehensive network
const majorArtists = [
    'The Beatles', 'Bob Dylan', 'Questlove', 'Taylor Swift', 'David Bowie',
    'John Lennon', 'Paul McCartney', 'Amy Winehouse', 'Radiohead', 'Beyoncé',
    'Patti Smith', 'Lou Reed', 'John Coltrane', 'Jimi Hendrix', 'Janis Joplin',
    'Miles Davis', 'Prince', 'Joni Mitchell', 'Neil Young', 'Frank Zappa',
    'Allen Ginsberg', 'Jack Kerouac', 'Leonard Cohen', 'Van Morrison',
    'The Rolling Stones', 'Led Zeppelin', 'Pink Floyd', 'The Doors',
    'Sonic Youth', 'Talking Heads', 'Television', 'Ramones', 'The Velvet Underground',
    'Bruce Springsteen', 'Johnny Cash', 'Woody Guthrie', 'Joan Baez',
    'Billie Holiday', 'Ella Fitzgerald', 'Duke Ellington', 'Charlie Parker',
    'Thelonious Monk', 'Art Blakey', 'Herbie Hancock', 'Weather Report',
    'Sly and the Family Stone', 'Stevie Wonder', 'Marvin Gaye', 'Aretha Franklin',
    'James Brown', 'Parliament-Funkadelic', 'Curtis Mayfield', 'Isaac Hayes'
];

let allConnections = [];
let totalQueries = 0;
let completedQueries = 0;

async function queryArtist(artist) {
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify({
            "query": `Show me all connections for ${artist} including collaborations, influences, and relationships`
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
                    console.log(`✅ ${artist}: Processing connections...`);

                    if (response.connections && response.connections.direct_connections) {
                        response.connections.direct_connections.forEach(entity => {
                            if (entity.top_connections) {
                                entity.top_connections.forEach(conn => {
                                    allConnections.push({
                                        source: artist,
                                        target: conn.target,
                                        relationship_type: conn.type,
                                        evidence: conn.evidence,
                                        confidence: conn.confidence || 0.8,
                                        source_type: 'musician',
                                        target_type: classifyEntity(conn.target)
                                    });
                                });
                            }
                        });
                    }

                    if (response.connections && response.connections.influence_networks) {
                        response.connections.influence_networks.forEach(influence => {
                            allConnections.push({
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

                    if (response.connections && response.connections.collaborative_clusters) {
                        response.connections.collaborative_clusters.forEach(collab => {
                            allConnections.push({
                                source: collab.entity1,
                                target: collab.entity2,
                                relationship_type: collab.type,
                                evidence: collab.context,
                                confidence: 0.9,
                                source_type: classifyEntity(collab.entity1),
                                target_type: classifyEntity(collab.entity2)
                            });
                        });
                    }

                    completedQueries++;
                    console.log(`   Progress: ${completedQueries}/${totalQueries} artists processed`);
                    resolve();
                } catch (error) {
                    console.log(`❌ ${artist}: Error parsing response`, error.message);
                    completedQueries++;
                    resolve();
                }
            });
        });

        req.on('error', (error) => {
            console.log(`❌ ${artist}: Request error`, error.message);
            completedQueries++;
            resolve();
        });

        req.write(postData);
        req.end();
    });
}

function classifyEntity(name) {
    if (!name) return 'entity';

    const musicians = ['Beatles', 'Dylan', 'Prince', 'Bowie', 'Lennon', 'McCartney', 'Radiohead'];
    const albums = ['Album', 'LP', 'Record'];
    const books = ['Book', 'Blues', 'Biography'];

    if (musicians.some(m => name.includes(m))) return 'musician';
    if (albums.some(a => name.includes(a))) return 'album';
    if (books.some(b => name.includes(b))) return 'book';

    return 'entity';
}

async function fetchCompleteNetwork() {
    totalQueries = majorArtists.length;
    console.log(`🚀 Querying ${totalQueries} major artists from the API...\n`);

    // Process artists in batches to avoid overwhelming the API
    const batchSize = 5;
    for (let i = 0; i < majorArtists.length; i += batchSize) {
        const batch = majorArtists.slice(i, i + batchSize);
        console.log(`\n📦 Processing batch ${Math.floor(i/batchSize) + 1}/${Math.ceil(majorArtists.length/batchSize)}`);

        await Promise.all(batch.map(artist => queryArtist(artist)));

        // Small delay between batches
        await new Promise(resolve => setTimeout(resolve, 1000));
    }

    console.log(`\n📊 COMPLETE API DATA COLLECTION RESULTS:`);
    console.log(`   Total connections collected: ${allConnections.length}`);
    console.log(`   Artists queried: ${completedQueries}/${totalQueries}`);

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

    // Create the massive network data
    const massiveNetwork = {
        metadata: {
            generated: new Date().toISOString(),
            version: 'api-complete-v1',
            total_relationships: uniqueConnections.length,
            total_entities: Object.keys(entityConnections).length,
            artists_queried: completedQueries,
            source: 'production-api'
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
            }))
    };

    // Save the massive network
    const fs = require('fs');
    fs.writeFileSync('massive-api-network.json', JSON.stringify(massiveNetwork, null, 2));

    const fileSize = fs.statSync('massive-api-network.json').size;
    console.log(`\n✅ Massive API network saved to: massive-api-network.json`);
    console.log(`📦 File size: ${(fileSize / 1024).toFixed(2)} KB`);

    console.log(`\n🌟 Top 20 Most Connected Entities:`);
    Object.entries(entityConnections)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 20)
        .forEach(([name, count], i) => {
            console.log(`   ${(i+1).toString().padStart(2)}. ${name.padEnd(30)} (${count} connections)`);
        });

    console.log(`\n🎯 This represents the REAL scale of your data lake!`);
}

fetchCompleteNetwork().catch(console.error);