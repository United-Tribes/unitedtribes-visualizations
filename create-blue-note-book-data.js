// Create Blue Note Records book visualization data
const https = require('https');
const fs = require('fs');

console.log('🎯 Creating Blue Note Records book network data...\n');

// Query for Blue Note Records book content
async function getBlueNoteBookData() {
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify({
            "query": "Tell me about The Cover Art of Blue Note Records book, including all artists, albums, visual designers, and relationships discussed in the book",
            "type": "creative_intelligence"
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
                    console.log('✅ Retrieved Blue Note book data from API');
                    resolve(response);
                } catch (error) {
                    console.log('❌ Error parsing API response:', error.message);
                    resolve({});
                }
            });
        });

        req.on('error', (error) => {
            console.log('❌ Request error:', error.message);
            resolve({});
        });

        req.write(postData);
        req.end();
    });
}

// Get additional Blue Note entities
async function getBlueNoteEntities() {
    const entities = [
        "Blue Note Records",
        "Reid Miles",
        "Francis Wolff",
        "Alfred Lion",
        "Lee Morgan",
        "John Coltrane",
        "Art Blakey",
        "Herbie Hancock",
        "Joe Henderson",
        "Dexter Gordon",
        "Jackie McLean",
        "Hank Mobley"
    ];

    const entityData = {};

    for (const entity of entities) {
        try {
            const response = await queryEntity(entity);
            if (response && response.connections) {
                entityData[entity] = response;
                console.log(`📊 Retrieved data for ${entity}`);
            }
        } catch (error) {
            console.log(`❌ Error getting ${entity}:`, error.message);
        }
    }

    return entityData;
}

async function queryEntity(entityName) {
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify({
            "query": `Tell me about ${entityName} and their connections to Blue Note Records, including albums, collaborations, and visual design work`,
            "type": "creative_intelligence"
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
                    resolve(response);
                } catch (error) {
                    resolve({});
                }
            });
        });

        req.on('error', (error) => {
            resolve({});
        });

        req.write(postData);
        req.end();
    });
}

// Main execution
async function main() {
    console.log('🔍 Gathering Blue Note Records book data...\n');

    // Get main book data
    const bookData = await getBlueNoteBookData();

    // Get related entity data
    const entityData = await getBlueNoteEntities();

    // Combine all data
    const combinedData = {
        query: "The Cover Art of Blue Note Records book network",
        timestamp: new Date().toISOString(),
        book_data: bookData,
        entity_data: entityData,
        metadata: {
            focus: "Blue Note Records book",
            entities_collected: Object.keys(entityData).length,
            created_by: "Blue Note Book Network Generator"
        }
    };

    // Save to file
    const filename = 'Documents/unitedtribes/blue-note-book-data.json';
    fs.writeFileSync(filename, JSON.stringify(combinedData, null, 2));

    console.log(`\n✅ Blue Note book network data saved to ${filename}`);
    console.log(`📊 Total entities: ${Object.keys(entityData).length}`);
    console.log('🎨 Ready for visualization!');
}

main().catch(console.error);