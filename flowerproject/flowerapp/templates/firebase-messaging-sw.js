// firebase-messaging-sw.js
importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging-compat.js');

firebase.initializeApp({
    apiKey:            "AIzaSyCzL0UB8Vs0qxENG0-i5S2FufK245RI-Qo",
    authDomain:        "bloomheaven-68ac5.firebaseapp.com",
    projectId:         "bloomheaven-68ac5",
    storageBucket:     "bloomheaven-68ac5.firebasestorage.app",
    messagingSenderId: "426547143093",
    appId:             "1:426547143093:web:e15bd460d426f2051439fc",
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
    self.registration.showNotification(payload.notification.title, {
        body: payload.notification.body,
        icon: '/static/logo.png'
    });
});