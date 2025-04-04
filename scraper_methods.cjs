/**
 * Show available methods in the Scraper class
 */

const { Scraper } = require('agent-twitter-client');

function showMethods() {
    try {
        // Create a new scraper instance
        const scraper = new Scraper();
        
        // Get all methods
        const methods = Object.getOwnPropertyNames(Object.getPrototypeOf(scraper));
        
        console.log('Available methods in Scraper class:');
        methods.forEach(method => {
            if (typeof scraper[method] === 'function' && method !== 'constructor') {
                console.log(`- ${method}`);
            }
        });
        
    } catch (error) {
        console.error('Error:', error.message);
    }
}

showMethods();