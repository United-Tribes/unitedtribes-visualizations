// Updated comprehensive Blue Note book data collection with richer queries
const https = require('https');
const fs = require('fs');

console.log('🎯 Collecting updated Blue Note Records book data with enhanced training material...\n');

// Enhanced query categories based on updated API training
const bookQueries = [
    // Core book content
    "The Cover Art of Blue Note Records book complete content analysis including all albums mentioned",
    "Blue Note Records visual identity and design philosophy from The Cover Art book",
    "Reid Miles complete design work and methodology for Blue Note album covers",
    "Francis Wolff photography and visual contributions to Blue Note aesthetic",
    "Alfred Lion's role in Blue Note visual identity and album packaging decisions",

    // Album cover analysis
    "Complete list of Blue Note album covers featured in The Cover Art book with design details",
    "Iconic Blue Note album covers and their visual design elements and typography",
    "Blue Note photography sessions and studio work by Francis Wolff",
    "Color palette and design principles used in Blue Note album covers",
    "Typography and text treatment in Blue Note Records album design",

    // Artist relationships
    "Art Blakey and Jazz Messengers album covers and visual presentation",
    "John Coltrane Blue Train album cover design and visual impact",
    "Lee Morgan The Sidewinder album cover and commercial success",
    "Horace Silver album covers and visual branding approach",
    "Thelonious Monk Blue Note album covers and artistic presentation",
    "Jimmy Smith Blue Note album covers and organ jazz visual identity",

    // Design and cultural context
    "Blue Note Records and mid-century modern design movement connections",
    "Jazz album cover design influence on graphic design history",
    "Blue Note visual identity impact on record industry design standards",
    "Cultural significance of Blue Note album covers in jazz history",
    "Blue Note Records and New York City cultural scene connections",

    // Contemporary relevance
    "Blue Note Records visual legacy and modern album cover design",
    "Collectors and vinyl culture appreciation of Blue Note cover art",
    "Blue Note Records reissue programs and visual presentation",
    "Contemporary artists influenced by Blue Note visual aesthetic",
    "Blue Note Records brand identity and modern marketing approach"
];

async function queryAPI(query) {
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify({
            "query": query,
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

async function main() {
    console.log('📚 Collecting updated Blue Note book data...\n');
    console.log(`📊 Total queries: ${bookQueries.length}\n`);

    const startTime = Date.now();
    const results = {};

    for (let i = 0; i < bookQueries.length; i++) {
        const query = bookQueries[i];
        console.log(`🔍 Query ${i + 1}/${bookQueries.length}: ${query.substring(0, 60)}...`);

        try {
            const response = await queryAPI(query);
            if (response && Object.keys(response).length > 0) {
                results[`query_${i + 1}`] = {
                    query: query,
                    response: response,
                    timestamp: new Date().toISOString()
                };
                console.log(`   ✅ Success`);
            } else {
                console.log(`   ⚠️  Empty response`);
            }

            // Delay between requests to respect API limits
            await new Promise(resolve => setTimeout(resolve, 250));

        } catch (error) {
            console.log(`   ❌ Error: ${error.message}`);
        }
    }

    const comprehensiveData = {
        book_title: "The Cover Art of Blue Note Records",
        query_timestamp: new Date().toISOString(),
        generation_time_minutes: Math.round((Date.now() - startTime) / 60000),
        total_queries: bookQueries.length,
        successful_queries: Object.keys(results).length,

        // Enhanced book data structure
        book_data: results,

        metadata: {
            focus: "Blue Note Records book comprehensive analysis",
            api_version: "Updated with enhanced training material",
            query_categories: [
                "Core book content analysis",
                "Visual identity and design philosophy",
                "Album cover detailed analysis",
                "Artist relationships and presentations",
                "Cultural and historical context",
                "Contemporary relevance and legacy"
            ],
            visualization_ready: true,
            created_by: "Updated Blue Note Book Data Generator"
        }
    };

    // Save to file
    const filename = 'Documents/unitedtribes/updated-blue-note-book-data.json';
    fs.writeFileSync(filename, JSON.stringify(comprehensiveData, null, 2));

    console.log(`\n✅ Updated Blue Note book data saved to ${filename}`);
    console.log(`📊 Statistics:`);
    console.log(`   • Total queries: ${comprehensiveData.total_queries}`);
    console.log(`   • Successful queries: ${comprehensiveData.successful_queries}`);
    console.log(`   • Generation time: ${comprehensiveData.generation_time_minutes} minutes`);
    console.log('🎨 Ready for enhanced network visualization!');
}

main().catch(console.error);