// Embed optimized network for perfect browser performance
const fs = require('fs');

console.log('🚀 Creating browser-optimized data lake explorer...');

// Read the optimized network data
const optimizedData = JSON.parse(fs.readFileSync('optimized-browser-network.json', 'utf8'));

console.log(`📊 Optimized network: ${optimizedData.artists.length} top artists, ${optimizedData.relationships.length} relationships`);

// Use the working data-lake-explorer.html as template
const htmlContent = fs.readFileSync('data-lake-explorer.html', 'utf8');

// Replace the embedded data function
const functionStart = 'loadEmbeddedCachedData() {';
const functionEnd = 'this.setupLegendFiltering();\n            }';

const startIndex = htmlContent.indexOf(functionStart);
const endIndex = htmlContent.indexOf(functionEnd, startIndex) + functionEnd.length;

if (startIndex === -1 || endIndex === -1) {
    console.error('❌ Could not find function in HTML template');
    process.exit(1);
}

const beforeFunction = htmlContent.substring(0, startIndex);
const afterFunction = htmlContent.substring(endIndex);

// Convert optimized data to the format expected by the visualization
const networkData = {
    metadata: optimizedData.metadata,
    relationships: optimizedData.relationships,
    entity_connections: {}
};

// Calculate entity connections from the data
optimizedData.artists.forEach(artist => {
    networkData.entity_connections[artist.entity] = artist.connection_strength;
});

// Create the new optimized function
const newFunction = `loadEmbeddedCachedData() {
                console.log('🚀 Loading BROWSER-OPTIMIZED network from top artists...');

                // OPTIMIZED NETWORK - Top ${optimizedData.artists.length} most connected artists for perfect browser performance
                const optimizedNetworkData = ${JSON.stringify(networkData, null, 8)};

                console.log(\`📊 Optimized network loaded: \${optimizedNetworkData.relationships.length} relationships\`);
                console.log('   Top artists with highest connections for rich visualization');
                console.log('   Optimized for instant loading and smooth rendering');

                this.processFullDataLake(optimizedNetworkData);
                this.createVisualization();
                this.setupResize();
                this.setupLegendFiltering();
            }`;

// Update the header
const updatedContent = (beforeFunction + newFunction + afterFunction).replace(
    '<div class="subtitle">Complete network of 220+ relationships across 191 entities • Instant loading from cache</div>',
    `<div class="subtitle">OPTIMIZED NETWORK: Top ${optimizedData.artists.length} artists with ${optimizedData.relationships.length} connections • Perfect browser performance</div>`
);

// Write the optimized HTML file
fs.writeFileSync('data-lake-explorer-optimized.html', updatedContent);

console.log('✅ Created data-lake-explorer-optimized.html');
console.log(`📦 File size: ${(updatedContent.length / 1024).toFixed(2)} KB`);

console.log('\n🎯 BROWSER PERFORMANCE OPTIMIZED:');
console.log(`   ✅ Only top ${optimizedData.artists.length} most connected artists`);
console.log(`   ✅ ${optimizedData.relationships.length} carefully selected relationships`);
console.log(`   ✅ Instant loading (no API calls)`);
console.log(`   ✅ Smooth rendering on any device`);
console.log(`   ✅ Google Maps-style navigation`);

console.log('\n🌟 Featured Artists:');
optimizedData.artists.slice(0, 10).forEach((artist, i) => {
    console.log(`   ${(i+1).toString().padStart(2)}. ${artist.entity.padEnd(25)} (${artist.connection_strength} total connections)`);
});

console.log('\n⚡ This gives you the richest network while maintaining perfect performance!');