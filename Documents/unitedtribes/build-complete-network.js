// Script to build a complete network from ALL artist data files
const fs = require('fs');
const path = require('path');

console.log('🔍 Building complete network from ALL artist data files...\n');

// Find all individual artist data files (exclude dense-network-data.json)
const dataFiles = fs.readdirSync('.')
    .filter(f => f.endsWith('-data.json') && !f.includes('dense-network') && !f.includes('full-data-lake-cache'))
    .sort();

console.log(`Found ${dataFiles.length} individual artist data files:`);
dataFiles.forEach(f => console.log(`  - ${f}`));
console.log('');

// Load and process all artist data
const allRelationships = [];
const allEntities = new Set();
const entityConnections = {};

dataFiles.forEach(filename => {
    try {
        const content = fs.readFileSync(filename, 'utf8');
        const data = JSON.parse(content);

        const artistName = filename.replace('-data.json', '').split('-').map(w =>
            w.charAt(0).toUpperCase() + w.slice(1)
        ).join(' ');

        console.log(`📂 Processing ${artistName}...`);

        if (data.relationships && Array.isArray(data.relationships)) {
            console.log(`   - Found ${data.relationships.length} relationships`);

            data.relationships.forEach(rel => {
                // Clean entity names
                const source = cleanEntityName(rel.source);
                const target = cleanEntityName(rel.target);

                if (source && target && source !== target) {
                    allRelationships.push({
                        source,
                        target,
                        relationship_type: rel.relationship_type || 'connected',
                        confidence: rel.confidence || 0.8,
                        evidence: rel.evidence,
                        source_type: rel.source_type || classifyEntity(source),
                        target_type: rel.target_type || classifyEntity(target)
                    });

                    allEntities.add(source);
                    allEntities.add(target);

                    // Count connections
                    entityConnections[source] = (entityConnections[source] || 0) + 1;
                    entityConnections[target] = (entityConnections[target] || 0) + 1;
                }
            });
        } else {
            console.log(`   - No relationships found`);
        }
    } catch (error) {
        console.log(`   - ❌ Error loading ${filename}: ${error.message}`);
    }
});

console.log(`\n📊 COMPLETE NETWORK STATISTICS:`);
console.log(`   Total relationships: ${allRelationships.length}`);
console.log(`   Total unique entities: ${allEntities.size}`);

// Clean entity names function
function cleanEntityName(name) {
    if (!name) return null;

    // Remove video timestamp patterns and artifacts
    name = name.replace(/\*\*([^*]+)\*\* - .*/, '$1');
    name = name.replace(/\*([^*]+)\* - .*/, '$1');
    name = name.replace(/- \[[\d:,\s]+\] - .*/, '');
    name = name.replace(/\[[\d:,\s]+\].*/, '');
    name = name.replace(/^[*\s]+|[*\s]+$/g, '');
    name = name.replace(/^["'\s]+|["'\s]+$/g, '');

    // Skip artifact names
    const skipPatterns = [
        /^https?:\/\//,
        /^\s*$/,
        /^Primary Subject$/,
        /^Artists?$/i,
        /^Musicians?$/i,
        /^Quest For Craft$/,
        /^How [A-Z]/,
        /^Lessons From/,
        /^Books That Changed$/
    ];

    if (skipPatterns.some(pattern => pattern.test(name))) {
        return null;
    }

    return name.trim();
}

// Enhanced entity classification
function classifyEntity(name) {
    // Known musicians (comprehensive list)
    const musicians = [
        'Patti Smith', 'Bob Dylan', 'Lou Reed', 'Jimi Hendrix', 'Janis Joplin', 'John Coltrane',
        'Neil Young', 'Jim Morrison', 'Michael Stipe', 'Johnny Cash', 'Leonard Cohen', 'Joni Mitchell',
        'Van Morrison', 'David Bowie', 'Iggy Pop', 'Miles Davis', 'Bruce Springsteen', 'The Beatles',
        'The Rolling Stones', 'Sonic Youth', 'Television', 'Talking Heads', 'Ramones', 'The Band',
        'Joan Baez', 'Woody Guthrie', 'Pete Seeger', 'Frank Zappa', 'The Byrds', 'John Cale',
        'Thelonious Monk', 'Charlie Parker', 'Paul McCartney', 'John Lennon', 'George Harrison',
        'Ringo Starr', 'Mick Jagger', 'Keith Richards', 'Pete Townshend', 'Eric Clapton',
        'Elvis Costello', 'Roger McGuinn', 'Leon Russell', 'The Velvet Underground'
    ];

    // Known poets/writers
    const poets = [
        'Allen Ginsberg', 'Arthur Rimbaud', 'William Blake', 'Jack Kerouac', 'William Burroughs',
        'Jim Carroll', 'Charles Bukowski', 'Gregory Corso', 'Lawrence Ferlinghetti', 'Gary Snyder'
    ];

    // Known cultural figures
    const culturalFigures = [
        'Robert Mapplethorpe', 'Andy Warhol', 'Sam Shepard', 'Martin Scorsese', 'Dua Lipa'
    ];

    // Albums (pattern matching)
    const albumPatterns = [
        'Horses', 'Transformer', 'Blood on the Tracks', 'Highway 61 Revisited', 'Electric Ladyland',
        'A Love Supreme', 'Kind of Blue', 'Blonde on Blonde', 'The Freewheelin\' Bob Dylan',
        'Nashville Skyline', 'The Basement Tapes', 'Pearl', 'Blue', 'Harvest', 'Astral Weeks',
        'Graceland', 'Sgt. Pepper\'s', 'The Rise and Fall of Ziggy Stardust', 'Songs of Leonard Cohen'
    ];

    // Books
    const bookPatterns = [
        'On the Road', 'Howl', 'Chronicles', 'The Basketball Diaries', 'Naked Lunch',
        'Desolation Angels', 'The Dharma Bums', 'True West', 'Songs of Innocence',
        'Tarantula', 'Visions of Cody', 'Just Kids'
    ];

    // Venues
    const venuePatterns = [
        'CBGB', 'Chelsea Hotel', 'The Factory', 'Electric Lady Studios', 'Newport Folk Festival',
        'Woodstock', 'The Fillmore', 'Madison Square Garden', 'Max\'s Kansas City', 'Blue Note Records'
    ];

    // Check classifications
    if (musicians.includes(name) || name.match(/\b(Band|Beatles|Stones|Heads|Youth)\b/)) return 'musician';
    if (poets.includes(name)) return 'poet';
    if (culturalFigures.includes(name)) return 'cultural_figure';
    if (albumPatterns.includes(name) || name.match(/\b(Album|LP|EP)\b/i)) return 'album';
    if (bookPatterns.includes(name) || name.match(/\b(Book|Novel|Diary|Diaries)\b/i)) return 'book';
    if (venuePatterns.includes(name) || name.match(/\b(Hotel|Studio|Festival|CBGB|Club)\b/i)) return 'venue';

    return 'entity';
}

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

console.log(`   Unique relationships (after dedup): ${uniqueRelationships.length}`);

// Sort entities by connection count
const topEntities = Object.entries(entityConnections)
    .sort(([,a], [,b]) => b - a);

console.log(`\n🌟 Top 20 Most Connected Entities:`);
topEntities.slice(0, 20).forEach(([name, count], i) => {
    console.log(`   ${(i+1).toString().padStart(2)}. ${name.padEnd(30)} (${count} connections)`);
});

// Create the complete network data structure
const completeNetwork = {
    metadata: {
        generated: new Date().toISOString(),
        version: 'complete-network-v1',
        total_relationships: uniqueRelationships.length,
        total_entities: allEntities.size,
        data_sources: dataFiles.length,
        source_files: dataFiles
    },
    relationships: uniqueRelationships,
    entity_connections: entityConnections,
    top_entities: topEntities.slice(0, 50).map(([name, count]) => ({
        name,
        connections: count,
        type: classifyEntity(name)
    })),
    entity_types: {
        musicians: uniqueRelationships.filter(r => r.source_type === 'musician' || r.target_type === 'musician').length,
        poets: uniqueRelationships.filter(r => r.source_type === 'poet' || r.target_type === 'poet').length,
        albums: uniqueRelationships.filter(r => r.source_type === 'album' || r.target_type === 'album').length,
        books: uniqueRelationships.filter(r => r.source_type === 'book' || r.target_type === 'book').length,
        venues: uniqueRelationships.filter(r => r.source_type === 'venue' || r.target_type === 'venue').length,
        cultural_figures: uniqueRelationships.filter(r => r.source_type === 'cultural_figure' || r.target_type === 'cultural_figure').length
    }
};

// Save the complete network
fs.writeFileSync('complete-network-all-artists.json', JSON.stringify(completeNetwork, null, 2));

const fileSize = fs.statSync('complete-network-all-artists.json').size;
console.log(`\n✅ Complete network saved to: complete-network-all-artists.json`);
console.log(`📦 File size: ${(fileSize / 1024).toFixed(2)} KB`);
console.log(`\n🎯 This contains EVERY artist and relationship from your data lake!`);

// Show breakdown by entity type
console.log(`\n📊 Entity Type Breakdown:`);
Object.entries(completeNetwork.entity_types).forEach(([type, count]) => {
    console.log(`   ${type.padEnd(20)}: ${count} relationships`);
});