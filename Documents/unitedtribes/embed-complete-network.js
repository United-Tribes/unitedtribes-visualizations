// Script to embed the COMPLETE network into HTML
const fs = require('fs');

console.log('📖 Reading complete network data...');
const completeData = JSON.parse(fs.readFileSync('complete-network-all-artists.json', 'utf8'));

console.log(`📊 Complete network contains:`);
console.log(`   - ${completeData.metadata.total_relationships} relationships`);
console.log(`   - ${completeData.metadata.total_entities} entities`);
console.log(`   - From ${completeData.metadata.data_sources} source files`);

// Read the HTML template (use the basic data-lake-explorer.html as template)
const htmlContent = fs.readFileSync('data-lake-explorer.html', 'utf8');

// Replace the loadEmbeddedCachedData function with the complete data
const functionStart = 'loadEmbeddedCachedData() {';
const functionEnd = 'this.setupLegendFiltering();\n            }';

const startIndex = htmlContent.indexOf(functionStart);
const endIndex = htmlContent.indexOf(functionEnd, startIndex) + functionEnd.length;

if (startIndex === -1 || endIndex === -1) {
    console.error('❌ Could not find loadEmbeddedCachedData function in HTML');
    process.exit(1);
}

const beforeFunction = htmlContent.substring(0, startIndex);
const afterFunction = htmlContent.substring(endIndex);

// Create the new function with complete data
const newFunction = `loadEmbeddedCachedData() {
                console.log('🚀 Loading COMPLETE network from ALL artist data files...');

                // COMPLETE NETWORK DATA - ALL ${completeData.metadata.data_sources} ARTISTS
                const completeNetworkData = ${JSON.stringify(completeData, null, 8)};

                console.log(\`📊 Loaded complete network: \${completeNetworkData.metadata.total_relationships} relationships, \${completeNetworkData.metadata.total_entities} entities\`);
                console.log('   Source files:', completeNetworkData.metadata.source_files);

                this.processFullDataLake(completeNetworkData);
                this.createVisualization();
                this.setupResize();
                this.setupLegendFiltering();
            }`;

// Combine the parts
const newHtmlContent = beforeFunction + newFunction + afterFunction;

// Update the header to reflect complete network
const updatedContent = newHtmlContent.replace(
    '<div class="subtitle">Complete network of 220+ relationships across 191 entities • Instant loading from cache</div>',
    `<div class="subtitle">COMPLETE NETWORK: ${completeData.metadata.total_relationships} relationships across ${completeData.metadata.total_entities} entities from ALL ${completeData.metadata.data_sources} artists • Instant loading</div>`
);

// Write the new file
fs.writeFileSync('data-lake-explorer-complete.html', updatedContent);

console.log('✅ Created data-lake-explorer-complete.html with ALL artist data embedded');
console.log(`📦 File size: ${(updatedContent.length / 1024).toFixed(2)} KB`);

console.log('\n🌟 This version includes EVERY artist with their full networks:');
completeData.top_entities.slice(0, 15).forEach((entity, i) => {
    console.log(`   ${(i+1).toString().padStart(2)}. ${entity.name.padEnd(30)} (${entity.connections} connections, ${entity.type})`);
});

console.log('\n🎯 Now every artist stands alone as their own complete hub!');