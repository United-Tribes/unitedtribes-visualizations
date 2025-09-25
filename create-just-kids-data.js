// Create Patti Smith Just Kids book visualization data
const https = require('https');
const fs = require('fs');

console.log('🎯 Creating Patti Smith Just Kids network data...\n');

// Query for Just Kids book content
async function getJustKidsData() {
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify({
            "query": "Tell me about Patti Smith's book Just Kids and all the artists, writers, musicians, poets, and visual artists mentioned in the book, including their relationships to Patti Smith and Robert Mapplethorpe",
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
                    console.log('✅ Retrieved Just Kids data from API');
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

// Get detailed data for Just Kids entities
async function getJustKidsEntities() {
    const entities = [
        "Patti Smith",
        "Robert Mapplethorpe",
        "Andy Warhol",
        "Allen Ginsberg",
        "Arthur Rimbaud",
        "William Burroughs",
        "Bob Dylan",
        "Jimi Hendrix",
        "Janis Joplin",
        "Lou Reed",
        "Jim Morrison",
        "John Coltrane",
        "Virginia Woolf",
        "Charles Bukowski",
        "Sam Shepard",
        "Jim Carroll",
        "Pablo Picasso",
        "Jean Genet"
    ];

    const entityData = {};

    for (const entity of entities) {
        try {
            const response = await queryEntity(entity);
            if (response && response.connections) {
                entityData[entity] = response;
                console.log(`📊 Retrieved data for ${entity}`);
            }
            // Add small delay to respect API limits
            await new Promise(resolve => setTimeout(resolve, 100));
        } catch (error) {
            console.log(`❌ Error getting ${entity}:`, error.message);
        }
    }

    return entityData;
}

async function queryEntity(entityName) {
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify({
            "query": `Tell me about ${entityName} and their connections to Patti Smith, Robert Mapplethorpe, the Chelsea Hotel scene, and the 1960s-70s NYC art world`,
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

// Get Patti Smith's existing comprehensive data
async function getExistingPattiData() {
    try {
        const existingData = fs.readFileSync('Documents/unitedtribes/patti-smith-data.json', 'utf8');
        console.log('📁 Found existing Patti Smith data file');
        return JSON.parse(existingData);
    } catch (error) {
        console.log('📁 No existing Patti Smith data file found, creating new...');
        return null;
    }
}

// Main execution
async function main() {
    console.log('🔍 Gathering Just Kids book network data...\n');

    // Get existing Patti Smith data
    const existingData = await getExistingPattiData();

    // Get main book data
    const bookData = await getJustKidsData();

    // Get related entity data
    const entityData = await getJustKidsEntities();

    // Combine all data
    const combinedData = {
        query: "Patti Smith Just Kids book network",
        timestamp: new Date().toISOString(),
        book_data: bookData,
        entity_data: entityData,
        existing_patti_data: existingData,
        metadata: {
            focus: "Just Kids book relationships",
            entities_collected: Object.keys(entityData).length,
            created_by: "Just Kids Network Generator"
        }
    };

    // Save to file
    const filename = 'Documents/unitedtribes/just-kids-data.json';
    fs.writeFileSync(filename, JSON.stringify(combinedData, null, 2));

    console.log(`\n✅ Just Kids network data saved to ${filename}`);
    console.log(`📊 Total entities: ${Object.keys(entityData).length}`);
    console.log('🎨 Ready for visualization!');
}

main().catch(console.error);