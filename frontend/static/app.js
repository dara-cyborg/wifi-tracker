// Minimal app.js - JavaScript utilities can go here
// Most app logic is in the HTML templates

function apiCall(endpoint, method = 'GET', data = null) {
    const options = { method };
    if (data) {
        options.headers = { 'Content-Type': 'application/json' };
        options.body = JSON.stringify(data);
    }
    return fetch(endpoint, options);
}
