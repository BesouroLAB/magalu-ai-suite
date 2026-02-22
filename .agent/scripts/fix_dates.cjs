const fs = require('fs');
const path = require('path');

const articlesDir = path.join(process.cwd(), 'public', 'articles');
const today = new Date('2026-01-15T00:00:00-03:00'); // Use explicit today date

function getRandomDate(start, end) {
    return new Date(start.getTime() + Math.random() * (end.getTime() - start.getTime()));
}

function formatDate(date) {
    // Format YYYY-MM-DD
    return date.toISOString().split('T')[0];
}

fs.readdir(articlesDir, (err, files) => {
    if (err) {
        console.error("Could not list directory", err);
        process.exit(1);
    }

    files.forEach(file => {
        if (!file.endsWith('.mdx')) return;

        const filePath = path.join(articlesDir, file);
        let content = fs.readFileSync(filePath, 'utf8');

        // Regex to find date: in frontmatter
        const dateRegex = /date:\s*['"]?(\d{4}-\d{2}-\d{2})['"]?/;
        const match = content.match(dateRegex);

        if (match) {
            const currentFileDate = new Date(match[1]);

            // If date is in the future relative to "today" (Jan 15, 2026)
            if (currentFileDate > today) {
                // Generate a random date in the past 6 months
                const sixMonthsAgo = new Date(today.getTime() - (180 * 24 * 60 * 60 * 1000));
                const newDate = getRandomDate(sixMonthsAgo, today);
                const newDateString = formatDate(newDate);

                const newContent = content.replace(dateRegex, `date: '${newDateString}'`);
                fs.writeFileSync(filePath, newContent);
                console.log(`Updated ${file}: ${match[1]} -> ${newDateString}`);
            } else {
                console.log(`Skipped ${file}: ${match[1]} (Already valid)`);
            }
        }
    });
});
