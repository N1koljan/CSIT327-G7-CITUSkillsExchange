// ui/static/ui/js/notifications.js

document.addEventListener('DOMContentLoaded', function() {
    // Ensure the user is logged in before trying to connect
    const isAuthenticated = document.body.dataset.isAuthenticated === 'true';

    if (isAuthenticated) {
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const notificationSocket = new WebSocket(
            `${protocol}://${window.location.host}/ws/notifications/`
        );

        notificationSocket.onopen = function(e) {
            console.log("Notification socket connected successfully.");
        };

        notificationSocket.onmessage = function(e) {
            const data = JSON.parse(e.data);
            console.log("Notification received:", data.message);

            // --- YOUR UI LOGIC HERE ---
            // This is where you make the notification appear on the screen.
            // For example, using a simple alert or a more complex toast library.
            displayNotification(data.message.text, data.message.url);
        };

        notificationSocket.onclose = function(e) {
            console.error('Notification socket closed unexpectedly. Attempting to reconnect...');
            // Optional: You could implement a reconnect logic here
        };

        notificationSocket.onerror = function(e) {
            console.error("An error occurred with the notification socket:", e);
        };

        function displayNotification(message, url) {
            // Example: Create a simple, clickable notification banner at the top of the page
            const notificationBar = document.createElement('div');
            notificationBar.className = 'notification-bar'; // Style this with CSS
            notificationBar.innerHTML = `<a href="${url}">${message}</a><span class="close-btn">&times;</span>`;

            document.body.prepend(notificationBar);

            notificationBar.querySelector('.close-btn').onclick = function() {
                notificationBar.remove();
            };

            // Optional: Make it disappear after a few seconds
            setTimeout(() => {
                if (notificationBar) {
                    notificationBar.remove();
                }
            }, 8000);
        }
    }
});