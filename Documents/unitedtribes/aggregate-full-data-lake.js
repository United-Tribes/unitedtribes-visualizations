// Script to aggregate the ENTIRE data lake into a single cached file
const fs = require('fs');
const path = require('path');

console.log('🔍 Aggregating entire data lake...\n');

// Find all JSON data files in the directory
const dataDir = '/Users/shanandelp/Documents/unitedtribes';
const files = fs.readdirSync(dataDir);
const dataFiles = files.filter(f => f.endsWith('-data.json') && !f.includes('dense-network'));

console.log(`Found ${dataFiles.length} data files to aggregate:`);
dataFiles.forEach(f => console.log(`  - ${f}`));

// Load all data files
const allData = {};
let totalRelationships = 0;
let totalEntities = new Set();

dataFiles.forEach(filename => {
    const filepath = path.join(dataDir, filename);
    try {
        const content = fs.readFileSync(filepath, 'utf8');
        const data = JSON.parse(content);

        // Extract entity name from filename or data
        let entityName = filename.replace('-data.json', '').replace(/-/g, ' ');
        entityName = entityName.split(' ').map(w =>
            w.charAt(0).toUpperCase() + w.slice(1)
        ).join(' ');

        allData[entityName] = data;

        // Count relationships and entities
        if (data.relationships) {
            totalRelationships += data.relationships.length;
            data.relationships.forEach(rel => {
                if (rel.source) totalEntities.add(rel.source);
                if (rel.target) totalEntities.add(rel.target);
            });
        }

        console.log(`✓ Loaded ${entityName}: ${data.relationships ? data.relationships.length : 0} relationships`);
    } catch (error) {
        console.log(`✗ Could not load ${filename}:`, error.message);
    }
});

// Clean entity names function
const cleanEntityName = (name) => {
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
        /^Musicians?$/i
    ];

    if (skipPatterns.some(pattern => pattern.test(name))) {
        return null;
    }

    return name.trim();
};

// Aggregate all relationships
const aggregatedRelationships = [];
const relationshipSet = new Set();
const entityConnections = {};

Object.entries(allData).forEach(([entityName, data]) => {
    if (!data.relationships) return;

    data.relationships.forEach(rel => {
        const source = cleanEntityName(rel.source);
        const target = cleanEntityName(rel.target);

        if (!source || !target || source === target) return;

        // Create unique key for deduplication
        const key = [source, target, rel.relationship_type].sort().join('|');
        if (relationshipSet.has(key)) return;

        relationshipSet.add(key);

        // Track connections per entity
        entityConnections[source] = (entityConnections[source] || 0) + 1;
        entityConnections[target] = (entityConnections[target] || 0) + 1;

        aggregatedRelationships.push({
            source,
            target,
            relationship_type: rel.relationship_type || 'connected',
            confidence: rel.confidence || 0.8,
            evidence: rel.evidence,
            source_type: rel.source_type || classifyEntity(source),
            target_type: rel.target_type || classifyEntity(target)
        });
    });
});

// Enhanced entity classification
function classifyEntity(name) {
    // Known musicians
    const musicians = [
        'Patti Smith', 'Bob Dylan', 'Lou Reed', 'Jimi Hendrix', 'Janis Joplin',
        'John Coltrane', 'Neil Young', 'Jim Morrison', 'Michael Stipe', 'Johnny Cash',
        'Leonard Cohen', 'Joni Mitchell', 'Van Morrison', 'David Bowie', 'Iggy Pop',
        'Miles Davis', 'Bruce Springsteen', 'The Beatles', 'The Rolling Stones',
        'Sonic Youth', 'Television', 'Talking Heads', 'Ramones', 'The Band',
        'Joan Baez', 'Woody Guthrie', 'Pete Seeger', 'Frank Zappa', 'The Byrds'
    ];

    // Known poets/writers
    const poets = [
        'Allen Ginsberg', 'Arthur Rimbaud', 'William Blake', 'Jack Kerouac',
        'William Burroughs', 'Jim Carroll', 'Charles Bukowski', 'Gregory Corso',
        'Lawrence Ferlinghetti', 'Gary Snyder'
    ];

    // Known cultural figures
    const culturalFigures = [
        'Robert Mapplethorpe', 'Andy Warhol', 'Sam Shepard'
    ];

    // Albums (pattern matching)
    const albums = [
        'Horses', 'Just Kids', 'Transformer', 'Blood on the Tracks',
        'Highway 61 Revisited', 'Electric Ladyland', 'A Love Supreme',
        'Kind of Blue', 'Blonde on Blonde', 'The Freewheelin\' Bob Dylan',
        'Nashville Skyline', 'The Basement Tapes', 'Pearl', 'Blue',
        'Harvest', 'Astral Weeks', 'Graceland', 'Sgt. Pepper\'s'
    ];

    // Books
    const books = [
        'On the Road', 'Howl', 'Chronicles', 'The Basketball Diaries',
        'Naked Lunch', 'Desolation Angels', 'The Dharma Bums', 'True West',
        'Songs of Innocence', 'Tarantula', 'Visions of Cody'
    ];

    // Venues
    const venues = [
        'CBGB', 'Chelsea Hotel', 'The Factory', 'Electric Lady Studios',
        'Newport Folk Festival', 'Woodstock', 'The Fillmore', 'Madison Square Garden',
        'Max\'s Kansas City', 'Blue Note Records'
    ];

    // Check classifications
    if (musicians.includes(name) || name.match(/\b(Band|Beatles|Stones|Heads)\b/)) return 'musician';
    if (poets.includes(name)) return 'poet';
    if (culturalFigures.includes(name)) return 'cultural_figure';
    if (albums.includes(name) || name.match(/\b(Album|LP|EP)\b/i)) return 'album';
    if (books.includes(name) || name.match(/\b(Book|Novel|Diary|Diaries)\b/i)) return 'book';
    if (venues.includes(name) || name.match(/\b(Hotel|Studio|Festival|CBGB|Club)\b/i)) return 'venue';

    return 'entity';
}

// Sort by connection count to identify major hubs
const sortedEntities = Object.entries(entityConnections)
    .sort(([,a], [,b]) => b - a);

console.log('\n📊 Data Lake Statistics:');
console.log(`  Total unique relationships: ${aggregatedRelationships.length}`);
console.log(`  Total unique entities: ${Object.keys(entityConnections).length}`);
console.log(`  Total data files: ${dataFiles.length}`);

console.log('\n🌟 Top 20 Most Connected Entities:');
sortedEntities.slice(0, 20).forEach(([name, count], i) => {
    console.log(`  ${(i+1).toString().padStart(2)}. ${name.padEnd(25)} (${count} connections)`);
});

// Identify clusters
const clusters = {
    'Beat Generation': ['Allen Ginsberg', 'Jack Kerouac', 'William Burroughs', 'Lawrence Ferlinghetti'],
    'Punk/CBGB': ['Patti Smith', 'Television', 'Ramones', 'Talking Heads', 'Richard Hell'],
    '60s Rock': ['Bob Dylan', 'Jimi Hendrix', 'Janis Joplin', 'The Beatles', 'The Rolling Stones'],
    'Jazz': ['John Coltrane', 'Miles Davis', 'Thelonious Monk', 'Charlie Parker'],
    'Folk': ['Joan Baez', 'Woody Guthrie', 'Pete Seeger', 'Phil Ochs'],
    'NYC Underground': ['Lou Reed', 'Andy Warhol', 'The Velvet Underground', 'John Cale']
};

// Create the full data lake cache
const fullDataLake = {
    metadata: {
        generated: new Date().toISOString(),
        version: '2.0',
        total_relationships: aggregatedRelationships.length,
        total_entities: Object.keys(entityConnections).length,
        data_sources: dataFiles.length
    },
    relationships: aggregatedRelationships,
    entity_connections: entityConnections,
    top_hubs: sortedEntities.slice(0, 50).map(([name, count]) => ({
        name,
        connections: count,
        type: classifyEntity(name)
    })),
    clusters,
    entity_types: {
        musicians: aggregatedRelationships.filter(r => r.source_type === 'musician' || r.target_type === 'musician').length,
        poets: aggregatedRelationships.filter(r => r.source_type === 'poet' || r.target_type === 'poet').length,
        albums: aggregatedRelationships.filter(r => r.source_type === 'album' || r.target_type === 'album').length,
        books: aggregatedRelationships.filter(r => r.source_type === 'book' || r.target_type === 'book').length,
        venues: aggregatedRelationships.filter(r => r.source_type === 'venue' || r.target_type === 'venue').length
    }
};

// Save the complete data lake
const outputPath = path.join(dataDir, 'full-data-lake-cache.json');
fs.writeFileSync(outputPath, JSON.stringify(fullDataLake, null, 2));

const fileSize = fs.statSync(outputPath).size;
console.log(`\n✅ Full data lake cached to: full-data-lake-cache.json`);
console.log(`📦 File size: ${(fileSize / 1024).toFixed(2)} KB`);
console.log(`🚀 This file can be embedded directly in HTML for instant loading!`);