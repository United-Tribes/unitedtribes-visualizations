// Create comprehensive Blue Note ecosystem data for rich visualization
const https = require('https');
const fs = require('fs');

console.log('🎯 Creating comprehensive Blue Note ecosystem data...\n');

// Comprehensive entity categories based on your requirements
const entityCategories = {
    // Visual Design Core
    visual_designers: ["Reid Miles", "Francis Wolff", "Alfred Lion"],

    // Contemporary Leadership
    current_leadership: ["Don Was"],

    // Founding Era
    founding_figures: ["Alfred Lion", "Francis Wolff", "Max Roach", "Art Tatum"],

    // Musical Artists by Era
    early_jazz_masters: ["Sidney Bechet", "James P. Johnson", "Meade Lux Lewis", "Albert Ammons"],
    bebop_revolutionaries: ["Thelonious Monk", "Bud Powell", "Fats Navarro", "Tadd Dameron"],
    civil_rights_era: ["Art Blakey", "Horace Silver", "Clifford Brown", "Lou Donaldson"],
    commercial_success: ["Lee Morgan", "Jimmy Smith", "Grant Green", "Stanley Turrentine"],
    revival_contemporary: ["Norah Jones", "Robert Glasper", "Ambrose Akinmusire", "Cecile McLorin Salvant"],

    // The Magnificent 7
    magnificent_seven: ["Lee Morgan", "John Coltrane", "Horace Silver", "Art Blakey", "Clifford Brown", "Sonny Rollins", "Hank Mobley"],

    // Key Supporting Artists
    house_musicians: ["Billy Higgins", "Paul Chambers", "Kenny Burrell", "Blue Mitchell"],

    // Iconic Albums (for cover art analysis)
    iconic_albums: ["The Sidewinder", "Blue Train", "Moanin'", "Song for My Father", "Go!", "Maiden Voyage", "Point of Departure"],

    // Documentary & Video Content
    documentary_content: ["Blue Note Records: The Covers", "The Visual World of Blue Note Records", "Blue Note Review", "Drop The Needle"],

    // Contemporary Vinyl/Collector Culture
    collector_culture: ["Tone Poet Series", "Blue Note Classic Vinyl Series", "SFJAZZ Vinyl Collection"],

    // Cultural Context
    political_figures: ["Martin Luther King Jr.", "Malcolm X", "Civil Rights Movement"],
    business_figures: ["Michael Cuscuna", "Bruce Lundvall", "Capitol Records"]
};

// Query the API for each category
async function queryEntityCategory(categoryName, entities) {
    console.log(`\n🔍 Collecting ${categoryName} data...`);
    const categoryData = {};

    for (const entity of entities) {
        try {
            const response = await queryEntity(entity, categoryName);
            if (response && response.connections) {
                categoryData[entity] = response;
                console.log(`   ✅ ${entity}`);
            }
            // Small delay to respect API limits
            await new Promise(resolve => setTimeout(resolve, 200));
        } catch (error) {
            console.log(`   ❌ ${entity}: ${error.message}`);
        }
    }

    return categoryData;
}

async function queryEntity(entityName, context) {
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify({
            "query": `Tell me about ${entityName} in the context of Blue Note Records, including their role in visual design, musical collaborations, cultural impact, and connections to album covers and the Blue Note visual identity legacy`,
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

// Get comprehensive documentary and video content data
async function getDocumentaryData() {
    console.log('\n🎬 Collecting documentary and video content data...');

    const documentaryQueries = [
        "Blue Note Records: The Covers documentary and the visual artists discussed",
        "The Visual World of Blue Note Records history and Reid Miles design philosophy",
        "Don Was Blue Note Review series and album packaging discussions",
        "Drop The Needle SFJAZZ collection and Blue Note vinyl collecting culture",
        "Top 10 Blue Note Records on Vinyl and iconic album covers"
    ];

    const documentaryData = {};

    for (const query of documentaryQueries) {
        try {
            const response = await queryDocumentary(query);
            if (response) {
                const key = query.split(' ')[0] + '_' + query.split(' ')[1];
                documentaryData[key] = response;
                console.log(`   ✅ ${key}`);
            }
            await new Promise(resolve => setTimeout(resolve, 300));
        } catch (error) {
            console.log(`   ❌ Error: ${error.message}`);
        }
    }

    return documentaryData;
}

async function queryDocumentary(query) {
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

// Get era-based timeline data
async function getTimelineData() {
    console.log('\n📅 Collecting historical timeline data...');

    const timelineQueries = [
        "Blue Note Records founding era 1939-1950 with Alfred Lion and Francis Wolff",
        "Blue Note bebop revolution 1950-1960 with Thelonious Monk and Bud Powell",
        "Blue Note civil rights era 1960-1970 with Art Blakey and Horace Silver",
        "Blue Note commercial success period 1970-1980 with Lee Morgan and Jimmy Smith",
        "Blue Note revival and contemporary era 1990-present with Norah Jones and Robert Glasper"
    ];

    const timelineData = {};

    for (const query of timelineQueries) {
        try {
            const response = await queryDocumentary(query);
            if (response) {
                const era = query.match(/era \d{4}-\d{4}/) || query.match(/period \d{4}-\d{4}/) || query.match(/\d{4}-\w+/);
                const key = era ? era[0].replace(' ', '_').replace('-', '_to_') : 'unknown_era';
                timelineData[key] = response;
                console.log(`   ✅ ${key}`);
            }
            await new Promise(resolve => setTimeout(resolve, 400));
        } catch (error) {
            console.log(`   ❌ Error: ${error.message}`);
        }
    }

    return timelineData;
}

// Main execution function
async function main() {
    console.log('🔍 Building comprehensive Blue Note ecosystem dataset...\n');
    console.log('📊 Categories to collect:');
    Object.keys(entityCategories).forEach(cat => {
        console.log(`   • ${cat}: ${entityCategories[cat].length} entities`);
    });

    const startTime = Date.now();

    // Collect all entity category data
    const entityData = {};
    for (const [categoryName, entities] of Object.entries(entityCategories)) {
        entityData[categoryName] = await queryEntityCategory(categoryName, entities);
    }

    // Collect documentary data
    const documentaryData = await getDocumentaryData();

    // Collect timeline data
    const timelineData = await getTimelineData();

    // Get Blue Note Records core entity data
    console.log('\n🎵 Collecting Blue Note Records core entity data...');
    const coreBlueNoteData = await queryEntity("Blue Note Records complete visual identity and cultural legacy", "comprehensive");

    // Combine all data into comprehensive structure
    const comprehensiveData = {
        query: "Blue Note Records comprehensive ecosystem",
        timestamp: new Date().toISOString(),
        generation_time_minutes: Math.round((Date.now() - startTime) / 60000),

        // Core Blue Note data
        blue_note_core: coreBlueNoteData,

        // Entity categories
        entity_categories: entityData,

        // Documentary and video content
        documentary_content: documentaryData,

        // Historical timeline
        historical_timeline: timelineData,

        // Metadata
        metadata: {
            focus: "Blue Note Records comprehensive ecosystem",
            total_entities: Object.values(entityCategories).flat().length,
            categories_collected: Object.keys(entityCategories).length,
            documentary_sources: Object.keys(documentaryData).length,
            timeline_periods: Object.keys(timelineData).length,
            created_by: "Blue Note Comprehensive Ecosystem Generator",
            visualization_type: "Rich multi-layered explorer"
        }
    };

    // Save to file
    const filename = 'Documents/unitedtribes/blue-note-comprehensive-data.json';
    fs.writeFileSync(filename, JSON.stringify(comprehensiveData, null, 2));

    console.log(`\n✅ Comprehensive Blue Note data saved to ${filename}`);
    console.log(`📊 Statistics:`);
    console.log(`   • Total entities: ${comprehensiveData.metadata.total_entities}`);
    console.log(`   • Categories: ${comprehensiveData.metadata.categories_collected}`);
    console.log(`   • Documentary sources: ${comprehensiveData.metadata.documentary_sources}`);
    console.log(`   • Timeline periods: ${comprehensiveData.metadata.timeline_periods}`);
    console.log(`   • Generation time: ${comprehensiveData.generation_time_minutes} minutes`);
    console.log('🎨 Ready for rich multi-layered visualization!');
}

main().catch(console.error);