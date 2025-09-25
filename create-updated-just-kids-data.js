// Updated comprehensive Just Kids book data collection with richer queries
const https = require('https');
const fs = require('fs');

console.log('🎯 Collecting updated Just Kids book data with enhanced training material...\n');

// Enhanced query categories for Patti Smith Just Kids book
const justKidsQueries = [
    // Core book narrative
    "Patti Smith Just Kids book complete narrative analysis and key relationships",
    "Robert Mapplethorpe and Patti Smith relationship development throughout Just Kids",
    "Chelsea Hotel cultural scene and artist community in Just Kids",
    "New York City 1970s art scene as depicted in Just Kids",
    "Beat Generation influence on Patti Smith as described in Just Kids",

    // Key figures and relationships
    "Andy Warhol Factory connections and interactions in Just Kids",
    "Allen Ginsberg mentorship and Beat poetry influence on Patti Smith",
    "Sam Shepard relationship and artistic collaboration with Patti Smith",
    "Lou Reed and Velvet Underground influence on Patti Smith's music",
    "Bob Dylan artistic influence and connection to Patti Smith",
    "Jim Morrison and Doors influence on Patti Smith's poetry and music",
    "William Burroughs Beat Generation connection to Patti Smith",
    "Jack Kerouac Beat poetry influence on Patti Smith's writing",

    // Art and music scenes
    "CBGB's and punk rock scene emergence with Patti Smith",
    "Max's Kansas City cultural significance in Just Kids narrative",
    "Photography and visual art world through Robert Mapplethorpe's career",
    "Poetry and literature influences on Patti Smith's artistic development",
    "Music industry and record label relationships in Patti Smith's career",

    // Cultural and artistic movements
    "Punk rock movement origins and Patti Smith's pioneering role",
    "New York bohemian artist community in 1970s as depicted in Just Kids",
    "Photography as art form and Robert Mapplethorpe's contributions",
    "Poetry performance and spoken word influence on punk music",
    "Fashion and style in 1970s New York art scene",

    // Contemporary connections
    "Patti Smith's continued relationships with surviving artists from Just Kids era",
    "Legacy of Chelsea Hotel artist community and cultural impact",
    "Influence of Just Kids book on contemporary understanding of 1970s art scene",
    "Robert Mapplethorpe's artistic legacy and museum exhibitions",
    "Patti Smith's Rock and Roll Hall of Fame recognition and artistic influence"
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
    console.log('📚 Collecting updated Just Kids book data...\n');
    console.log(`📊 Total queries: ${justKidsQueries.length}\n`);

    const startTime = Date.now();
    const results = {};

    for (let i = 0; i < justKidsQueries.length; i++) {
        const query = justKidsQueries[i];
        console.log(`🔍 Query ${i + 1}/${justKidsQueries.length}: ${query.substring(0, 60)}...`);

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
        book_title: "Just Kids by Patti Smith",
        query_timestamp: new Date().toISOString(),
        generation_time_minutes: Math.round((Date.now() - startTime) / 60000),
        total_queries: justKidsQueries.length,
        successful_queries: Object.keys(results).length,

        // Enhanced book data structure
        book_data: results,

        metadata: {
            focus: "Patti Smith Just Kids comprehensive relationship analysis",
            api_version: "Updated with enhanced training material",
            query_categories: [
                "Core narrative and relationships",
                "Key cultural figures and connections",
                "Art and music scene contexts",
                "Cultural and artistic movements",
                "Contemporary legacy and influence"
            ],
            visualization_ready: true,
            created_by: "Updated Just Kids Data Generator"
        }
    };

    // Save to file
    const filename = 'Documents/unitedtribes/updated-just-kids-data.json';
    fs.writeFileSync(filename, JSON.stringify(comprehensiveData, null, 2));

    console.log(`\n✅ Updated Just Kids data saved to ${filename}`);
    console.log(`📊 Statistics:`);
    console.log(`   • Total queries: ${comprehensiveData.total_queries}`);
    console.log(`   • Successful queries: ${comprehensiveData.successful_queries}`);
    console.log(`   • Generation time: ${comprehensiveData.generation_time_minutes} minutes`);
    console.log('🎨 Ready for enhanced network visualization!');
}

main().catch(console.error);