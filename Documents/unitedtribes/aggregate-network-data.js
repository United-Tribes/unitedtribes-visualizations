// Script to aggregate multiple artist networks into dense clusters
const fs = require('fs');

// Load all the entity data files
const loadEntityData = (filename) => {
    try {
        const data = JSON.parse(fs.readFileSync(filename, 'utf8'));
        return data.relationships || [];
    } catch (error) {
        console.log(`Could not load ${filename}:`, error.message);
        return [];
    }
};

const pattiSmithData = loadEntityData('/Users/shanandelp/Documents/unitedtribes/patti-smith-full-data.json');
const bobDylanData = loadEntityData('/Users/shanandelp/Documents/unitedtribes/bob-dylan-data.json');
const louReedData = loadEntityData('/Users/shanandelp/Documents/unitedtribes/lou-reed-data.json');
const jimiHendrixData = loadEntityData('/Users/shanandelp/Documents/unitedtribes/jimi-hendrix-data.json');
const janisJoplinData = loadEntityData('/Users/shanandelp/Documents/unitedtribes/janis-joplin-data.json');
const allenGinsbergData = loadEntityData('/Users/shanandelp/Documents/unitedtribes/allen-ginsberg-data.json');
const johnColtraneData = loadEntityData('/Users/shanandelp/Documents/unitedtribes/john-coltrane-data.json');

// Combine all relationships
const allRelationships = [
    ...pattiSmithData,
    ...bobDylanData,
    ...louReedData,
    ...jimiHendrixData,
    ...janisJoplinData,
    ...allenGinsbergData,
    ...johnColtraneData
];

console.log(`Total relationships found: ${allRelationships.length}`);

// Filter for clean entity names (remove video timestamps and artifacts)
const cleanEntityName = (name) => {
    if (!name) return null;

    // Remove video timestamp patterns
    name = name.replace(/\*\*([^*]+)\*\* - .*/, '$1');
    name = name.replace(/\*([^*]+)\* - .*/, '$1');
    name = name.replace(/- \[[\d:,\s]+\] - .*/, '');
    name = name.replace(/\[[\d:,\s]+\].*/, '');

    // Remove leading/trailing asterisks and quotes
    name = name.replace(/^\*+|\*+$/g, '').replace(/^"+|"+$/g, '').trim();

    // Only skip truly generic or artifact names - be much more permissive
    const skipPatterns = [
        /^Primary Subject$/,
        /^Artists?$/i,
        /^Musicians?$/i,
        /^Quest For Craft$/,
        /^How [A-Z]/,
        /^Lessons From/,
        /^Books That Changed$/,
        /https?:\/\//,
        /^\s*$/,
        /^.*- \[.*\]$/  // Video timestamp artifacts
    ];

    if (skipPatterns.some(pattern => pattern.test(name))) {
        return null;
    }

    return name;
};

// Process and deduplicate relationships
const processedRelationships = [];
const relationshipSet = new Set();

allRelationships.forEach(rel => {
    const source = cleanEntityName(rel.source);
    const target = cleanEntityName(rel.target);

    if (!source || !target || source === target) return;

    // Create relationship key for deduplication
    const key = [source, target, rel.relationship_type].sort().join('|');
    if (relationshipSet.has(key)) return;

    relationshipSet.add(key);
    processedRelationships.push({
        source,
        target,
        relationship_type: rel.relationship_type,
        confidence: rel.confidence || 0.8,
        evidence: rel.evidence
    });
});

// Classify entity types based on known patterns
const classifyEntity = (name) => {
    const musicians = [
        'Bob Dylan', 'Lou Reed', 'Jimi Hendrix', 'Janis Joplin', 'John Coltrane', 'Patti Smith',
        'Neil Young', 'Jim Morrison', 'Michael Stipe', 'Adele', 'Stevie Wonder', 'Johnny Winter',
        'Brian Jones', 'Pete Townshend', 'Eric Clapton', 'George Harrison', 'John Lennon',
        'Paul McCartney', 'Ringo Starr', 'Mick Jagger', 'Keith Richards', 'David Bowie',
        'Iggy Pop', 'Frank Zappa', 'Miles Davis', 'Thelonious Monk', 'Charlie Parker',
        'Joan Baez', 'Woody Guthrie', 'Pete Seeger', 'The Band', 'The Beatles', 'Johnny Cash',
        'Leonard Cohen', 'Joni Mitchell', 'Van Morrison', 'The Rolling Stones'
    ];

    const poets = [
        'Allen Ginsberg', 'Arthur Rimbaud', 'William Blake', 'Jack Kerouac', 'William Burroughs',
        'Gary Snyder', 'Lawrence Ferlinghetti', 'Jim Carroll', 'Charles Bukowski', 'Gregory Corso'
    ];

    const books = [
        'Just Kids', 'On the Road', 'Howl', 'Chronicles', 'Tarantula', 'The Basketball Diaries',
        'Desolation Angels', 'Naked Lunch', 'The Dharma Bums', 'Visions of Cody'
    ];

    const albums = [
        'Horses', 'Transformer', 'Berlin', 'Blood on the Tracks', 'Highway 61 Revisited',
        'Electric Ladyland', 'Are You Experienced', 'Pearl', 'A Love Supreme', 'Blonde on Blonde',
        'The Freewheelin\' Bob Dylan', 'Nashville Skyline', 'John Wesley Harding', 'Oh Mercy',
        'Shot of Love', 'The Basement Tapes', 'New Morning', 'Street‐Legal', 'Knocked Out Loaded'
    ];

    const venues = [
        'Chelsea Hotel', 'CBGB', 'The Fillmore', 'Madison Square Garden', 'Newport Folk Festival',
        'Woodstock', 'The Factory', 'Electric Lady Studios'
    ];

    if (musicians.includes(name)) return 'musician';
    if (poets.includes(name)) return 'poet';
    if (books.includes(name)) return 'book';
    if (albums.includes(name)) return 'album';
    if (venues.includes(name)) return 'venue';
    if (name.includes('Hotel') || name.includes('CBGB')) return 'venue';

    // Pattern-based classification for more entities
    if (name.match(/\b(Album|LP|EP)\b/i)) return 'album';
    if (name.match(/\b(Book|Novel|Poem|Poetry)\b/i)) return 'book';
    if (name.match(/\b(Festival|Concert|Club|Studio|Theatre)\b/i)) return 'venue';

    return 'cultural_figure';
};

// Add entity type to relationships
const enrichedRelationships = processedRelationships.map(rel => ({
    ...rel,
    source_type: classifyEntity(rel.source),
    target_type: classifyEntity(rel.target)
}));

// Count connections per entity to find central nodes
const connectionCounts = {};
enrichedRelationships.forEach(rel => {
    connectionCounts[rel.source] = (connectionCounts[rel.source] || 0) + 1;
    connectionCounts[rel.target] = (connectionCounts[rel.target] || 0) + 1;
});

// Sort by connection count and take top entities for dense network
const topEntities = Object.entries(connectionCounts)
    .sort(([,a], [,b]) => b - a)
    .slice(0, 100) // Top 100 most connected entities for much denser network
    .map(([name]) => name);

// Filter relationships to only include top entities
const denseRelationships = enrichedRelationships.filter(rel =>
    topEntities.includes(rel.source) && topEntities.includes(rel.target)
);

console.log(`Dense network: ${topEntities.length} entities, ${denseRelationships.length} relationships`);
console.log(`Top 10 most connected:`, Object.entries(connectionCounts)
    .sort(([,a], [,b]) => b - a)
    .slice(0, 10)
    .map(([name, count]) => `${name} (${count})`)
);

// Output the dense network data
const output = {
    relationships: denseRelationships,
    entity_counts: connectionCounts,
    total_entities: topEntities.length,
    total_relationships: denseRelationships.length
};

fs.writeFileSync('/Users/shanandelp/Documents/unitedtribes/dense-network-data.json', JSON.stringify(output, null, 2));
console.log('Dense network data saved to dense-network-data.json');