// Create targeted Blue Note book album and artist data for clustering visualization
const https = require('https');
const fs = require('fs');

console.log('🎯 Collecting Blue Note book albums and artists data for clustering...\n');

// Targeted queries for specific albums and artists mentioned in the Blue Note book
const albumArtistQueries = [
    // Core iconic albums from the book with their complete artist lineups
    "Blue Train album by John Coltrane complete musician lineup Lee Morgan Curtis Fuller Kenny Drew Paul Chambers Art Blakey",
    "The Sidewinder album by Lee Morgan complete musician lineup Joe Henderson Barry Harris Bob Cranshaw Billy Higgins",
    "Moanin' album by Art Blakey and Jazz Messengers complete musician lineup Lee Morgan Benny Golson Bobby Timmons Jymie Merritt",
    "Song for My Father album by Horace Silver complete musician lineup Carmell Jones Joe Henderson Roger Davis Donald Byrd",
    "Maiden Voyage album by Herbie Hancock complete musician lineup Freddie Hubbard George Coleman Ron Carter Tony Williams",
    "Page One album by Joe Henderson complete musician lineup Kenny Dorham McCoy Tyner Butch Warren Pete La Roca",
    "Go! album by Dexter Gordon complete musician lineup Sonny Clark Butch Warren Billy Higgins",
    "Point of Departure album by Andrew Hill complete musician lineup Kenny Dorham Eric Dolphy Joe Henderson Richard Davis Tony Williams",
    "Una Mas album by Kenny Dorham complete musician lineup Joe Henderson Herbie Hancock Butch Warren Tony Williams",
    "Spring album by Tony Williams complete musician lineup Sam Rivers Wayne Shorter Herbie Hancock Gary Peacock",

    // Additional albums referenced in the book
    "Monk's Music album by Thelonious Monk complete musician lineup Ray Copeland Gigi Gryce Coleman Hawkins John Coltrane Wilbur Ware Art Blakey",
    "Six Pieces of Silver album by Horace Silver complete musician lineup Donald Byrd Hank Mobley Doug Watkins Louis Hayes",
    "Roll Call album by Hank Mobley complete musician lineup Freddie Hubbard Wynton Kelly Paul Chambers Art Blakey",
    "Destination Out album by Jackie McLean complete musician lineup Grachan Moncur III Bobby Hutcherson Larry Ridley Roy Haynes",
    "Down and Out Blues album by Sonny Clark complete musician lineup Ike Quebec Grant Green Sam Jones Louis Hayes",

    // House musicians and sidemen who appear on multiple Blue Note albums
    "Paul Chambers bassist Blue Note Records albums appearances and collaborations",
    "Art Blakey drummer Blue Note Records albums appearances and Jazz Messengers lineups",
    "Billy Higgins drummer Blue Note Records albums appearances and collaborations",
    "Kenny Burrell guitarist Blue Note Records albums appearances and collaborations",
    "Blue Mitchell trumpeter Blue Note Records albums appearances and collaborations",
    "Curtis Fuller trombonist Blue Note Records albums appearances and collaborations",
    "Hank Mobley saxophonist Blue Note Records albums appearances and collaborations",
    "Joe Henderson saxophonist Blue Note Records albums appearances and collaborations",

    // Cover art specific queries
    "Blue Note album covers featuring Reid Miles typography and design Blue Train The Sidewinder Moanin'",
    "Francis Wolff photography Blue Note album covers session musicians portraits",
    "Blue Note album covers color schemes and visual design patterns iconic albums",

    // Era-based album groupings
    "Blue Note hard bop era albums 1956-1963 Art Blakey Horace Silver Clifford Brown",
    "Blue Note modal jazz era albums 1959-1965 John Coltrane Joe Henderson Andrew Hill",
    "Blue Note avant-garde era albums 1963-1968 Jackie McLean Eric Dolphy Sam Rivers"
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
    console.log('📚 Collecting Blue Note book albums and artists data...\n');
    console.log(`📊 Total queries: ${albumArtistQueries.length}\n`);

    const startTime = Date.now();
    const results = {};

    for (let i = 0; i < albumArtistQueries.length; i++) {
        const query = albumArtistQueries[i];
        console.log(`🔍 Query ${i + 1}/${albumArtistQueries.length}: ${query.substring(0, 70)}...`);

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
            await new Promise(resolve => setTimeout(resolve, 300));

        } catch (error) {
            console.log(`   ❌ Error: ${error.message}`);
        }
    }

    const comprehensiveData = {
        focus: "Blue Note Records book albums and artists clustering data",
        query_timestamp: new Date().toISOString(),
        generation_time_minutes: Math.round((Date.now() - startTime) / 60000),
        total_queries: albumArtistQueries.length,
        successful_queries: Object.keys(results).length,

        // Album and artist clustering data
        album_artist_data: results,

        metadata: {
            purpose: "Clustering visualization of Blue Note book albums and their musicians",
            api_version: "Enhanced with album lineup details",
            query_categories: [
                "Iconic album complete lineups",
                "House musicians and sidemen",
                "Cover art visual design",
                "Era-based album groupings"
            ],
            visualization_ready: true,
            created_by: "Blue Note Albums Artists Clustering Generator"
        }
    };

    // Save to file
    const filename = 'Documents/unitedtribes/blue-note-albums-artists-data.json';
    fs.writeFileSync(filename, JSON.stringify(comprehensiveData, null, 2));

    console.log(`\n✅ Blue Note albums and artists data saved to ${filename}`);
    console.log(`📊 Statistics:`);
    console.log(`   • Total queries: ${comprehensiveData.total_queries}`);
    console.log(`   • Successful queries: ${comprehensiveData.successful_queries}`);
    console.log(`   • Generation time: ${comprehensiveData.generation_time_minutes} minutes`);
    console.log('🎨 Ready for album-artist clustering visualization!');
}

main().catch(console.error);