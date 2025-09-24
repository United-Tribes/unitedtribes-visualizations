// Script to embed the complete cached data into the HTML file
const fs = require('fs');

console.log('📖 Reading full cache data...');
const cacheData = JSON.parse(fs.readFileSync('full-data-lake-cache.json', 'utf8'));

console.log(`📊 Cache contains: ${cacheData.relationships.length} relationships, ${cacheData.metadata.total_entities} entities`);

// Read the HTML template
const htmlContent = fs.readFileSync('data-lake-explorer.html', 'utf8');

// Find the embedded data section and replace it with the full cache
const startMarker = 'const embeddedData = {';
const endMarker = '};';

const startIndex = htmlContent.indexOf(startMarker);
const endIndex = htmlContent.indexOf(endMarker, startIndex) + endMarker.length;

if (startIndex === -1 || endIndex === -1) {
    console.error('❌ Could not find embedded data section in HTML');
    process.exit(1);
}

const beforeData = htmlContent.substring(0, startIndex);
const afterData = htmlContent.substring(endIndex);

// Create the new embedded data string
const newEmbeddedData = `const embeddedData = ${JSON.stringify(cacheData, null, 8)};`;

// Combine the parts
const newHtmlContent = beforeData + newEmbeddedData + afterData;

// Write the new file
fs.writeFileSync('data-lake-explorer-full.html', newHtmlContent);

console.log('✅ Created data-lake-explorer-full.html with complete embedded cache');
console.log(`📦 File size: ${(newHtmlContent.length / 1024).toFixed(2)} KB`);

// Show some key stats
console.log('\n🌟 Top entities by connections:');
Object.entries(cacheData.entity_connections)
    .sort(([,a], [,b]) => b - a)
    .slice(0, 15)
    .forEach(([name, count], i) => {
        console.log(`  ${(i+1).toString().padStart(2)}. ${name.padEnd(30)} (${count} connections)`);
    });