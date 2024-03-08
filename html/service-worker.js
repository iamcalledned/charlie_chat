self.addEventListener('install', event => {
    console.log('Service worker installing...');
    // Put your install code here
});

self.addEventListener('activate', event => {
    console.log('Service worker activating...');
    // Put your activation code here
});

self.addEventListener('fetch', event => {
    console.log('Fetching:', event.request.url);
    // Put your fetch event code here
});


