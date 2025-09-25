# United Tribes Visualizations

Interactive network visualizations exploring cultural connections in music, literature, and art.

## Live Demo

🌐 **[View Live Visualizations](http://unitedtribes-visualizations-1758769416.s3-website-us-east-1.amazonaws.com/)**

### Featured Visualizations

- **[Just Kids Network](http://unitedtribes-visualizations-1758769416.s3-website-us-east-1.amazonaws.com/just-kids-all-entities-network.html)** - Interactive exploration of Patti Smith's memoir with 154+ people, books, albums, and cultural connections from the 1960s-70s NYC scene

- **[Blue Note Records Network](http://unitedtribes-visualizations-1758769416.s3-website-us-east-1.amazonaws.com/blue-note-comprehensive-network.html)** - Comprehensive network of jazz legends, albums, and musical relationships from the legendary label

## Features

- **Interactive D3.js Networks** - Explore complex cultural relationships through force-directed visualizations
- **Universal Entity Focusing** - Click any entity to highlight its connections and see detailed information
- **Comprehensive Tooltips** - Rich contextual information for every person, album, book, and cultural artifact
- **Smart Categorization** - Color-coded entities (musicians, writers, albums, books, venues, movements)
- **Responsive Design** - Works seamlessly on desktop and mobile devices

## Technical Details

### Architecture
- Built with D3.js v7 for robust network visualization
- Self-contained HTML files with embedded data (no external API dependencies)
- Comprehensive entity extraction from cultural intelligence APIs
- Strategic connection mapping based on historical and artistic relationships

### Data Sources
- Comprehensive API queries covering biographical, artistic, and cultural connections
- Manual curation of Beat Generation, punk rock, and jazz relationships
- 600+ KB of structured cultural intelligence data per visualization

### Hosting
- Deployed on AWS S3 with static website hosting
- CloudFront-ready for global content delivery
- Cost-effective hosting (~$0.01/month)

## Local Development

```bash
# Clone the repository
git clone https://github.com/[username]/unitedtribes-visualizations.git
cd unitedtribes-visualizations

# Serve locally (optional)
cd public
python3 -m http.server 8080
# Visit http://localhost:8080
```

## File Structure

```
├── Documents/unitedtribes/          # Source visualization files
├── public/                          # Production hosting files
├── create-*.js                      # Data generation scripts
├── *.json                          # Comprehensive API response data
└── README.md                       # This file
```

## Credits

- **Visualization Framework**: D3.js force-directed networks
- **Cultural Intelligence**: United Tribes API
- **Design Philosophy**: Shanan's clean, minimalist aesthetic
- **Generated with**: [Claude Code](https://claude.ai/code)

---

*Exploring the interconnected nature of cultural expression through interactive visualization*