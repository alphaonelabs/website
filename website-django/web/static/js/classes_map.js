document.addEventListener("DOMContentLoaded", function () {
  // Initialize Map with a default location
  var map = L.map("map").setView([40.7128, -74.006], 5);

  // Load OpenStreetMap tiles
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  // User location marker
  var userMarker = null;

  // Custom icon CSS
  var userIcon = L.icon({
    iconUrl: "/static/images/red-dot.png",
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32],
  }); // <-- Closing bracket added

  var defaultIcon = L.icon({
    iconUrl: "/static/images/blue-dot.png",
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32],
  });

  var highlightedIcon = L.icon({
    iconUrl: "/static/images/yellow-dot.png", // Use a different color
    iconSize: [38, 38], // Slightly bigger for emphasis
    iconAnchor: [19, 38],
    popupAnchor: [0, -38],
  });

  // Function to get user location
  function getUserLocation() {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        function (position) {
          var userLat = position.coords.latitude;
          var userLng = position.coords.longitude;

          // Recenter map to user's live location
          map.setView([userLat, userLng], 12);

          // Add marker for user's live location
          if (userMarker) {
            userMarker.setLatLng([userLat, userLng]);
          } else {
            userMarker = L.marker([userLat, userLng], {
              icon: userIcon,
            })
              .addTo(map)
              .bindPopup("Your Location")
              .openPopup();
          }
        },
        function (error) {
          console.error("Error getting location:", error);
          alert(
            "Location access denied. Please enable it in your browser settings."
          );
        }
      );
    } else {
      alert("Geolocation is not supported by this browser.");
    }
  }

  // Extract session data from DOM elements
  function extractSessionData() {
    var sessionData = [];
    var sessionElements = document.querySelectorAll(".session-item");

    sessionElements.forEach(function (element) {
      sessionData.push({
        lat: parseFloat(element.getAttribute("data-lat")) || 0,
        lng: parseFloat(element.getAttribute("data-lng")) || 0,
        title: element.getAttribute("data-title") || "Unnamed Session",
        date: element.getAttribute("data-date") || "No date specified",
        location:
          element.getAttribute("data-location") || "No location specified",
        teacher: element.getAttribute("data-teacher") || "No teacher specified",
        course_title:
          element.getAttribute("data-course-title") || "No course specified",
        start_time: element.getAttribute("data-start-time") || "TBD",
        end_time: element.getAttribute("data-end-time") || "TBD",
        url: element.getAttribute("data-enrollment-url") || "No url specified",
      });
    });

    return sessionData;
  }

  // Load session locations from extracted data
  var markers = [];
  var sessionData = extractSessionData();
  console.log(sessionData);
  // Check if we have session data
  if (sessionData.length > 0) {
    sessionData.forEach((session) => {
      if (isNaN(session.lat) || isNaN(session.lng)) {
        console.warn("Invalid coordinates for session:", session.title);
        return;
      }

      var popupContent = `
    <div>
        <strong>${session.title}</strong><br />
        ${session.location}<br />
        <strong>Teacher:</strong> ${session.teacher || "N/A"}<br />
        <strong>Course:</strong> ${session.course_title || "N/A"}<br />
        <strong>Start:</strong> ${session.start_time}<br />
        <strong>End:</strong> ${session.end_time}<br />

        <div style="margin-top: 10px;">
            <!-- Get Directions Button -->
            <a href="#" class="directions-btn" data-lat="${
              session.lat
            }" data-lng="${session.lng}">
                <button style="padding: 5px 10px; cursor: pointer;">Get Directions</button>
            </a>

            <!-- Enroll Button -->
            <a href="${session.url}" target="_blank">
                <button style="padding: 5px 10px; cursor: pointer;">Enroll</button>
            </a>
        </div>
    </div>
`;

      var marker = L.marker([session.lat, session.lng], {
        icon: defaultIcon,
      })
        .addTo(map)
        .bindPopup(popupContent);

      markers.push({
        lat: session.lat,
        lng: session.lng,
        marker: marker,
      });
    });
  }

  // Show 'No results' message if no sessions
  var hasSessionsElement = document.getElementById("session-data");
  var hasSessions =
    hasSessionsElement.getAttribute("data-has-sessions") === "true";

  if (!hasSessions) {
    document.getElementById("no-results").classList.remove("hidden");
  }

  // Get directions functionality
  document.addEventListener("click", function (event) {
    if (event.target.closest(".directions-btn")) {
      event.preventDefault();
      var target = event.target.closest(".directions-btn");

      var sessionLat = target.getAttribute("data-lat");
      var sessionLng = target.getAttribute("data-lng");

      // Fetch user's location dynamically
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          function (position) {
            var userLat = position.coords.latitude;
            var userLng = position.coords.longitude;

            // Construct the directions URL
            var directionsUrl = `https://www.openstreetmap.org/directions?from=${userLat},${userLng}&to=${sessionLat},${sessionLng}`;

            // Open in a new tab
            window.open(directionsUrl, "_blank");
          },
          function (error) {
            alert(
              "Unable to access location. Please enable location services."
            );
          }
        );
      } else {
        alert("Geolocation is not supported by this browser.");
      }
    }
  });

  // Locate Button Click Event
  let activeMarker = null; // Store the currently highlighted marker

  document.querySelectorAll(".locate-btn").forEach((button) => {
    button.addEventListener("click", function () {
      var lat = parseFloat(this.getAttribute("data-lat"));
      var lng = parseFloat(this.getAttribute("data-lng"));

      // Set map view to the new location
      map.setView([lat, lng], 14);

      // Reset the previous marker if any
      if (activeMarker) {
        activeMarker.setIcon(defaultIcon); // Reset to default icon
      }

      // Find the marker that matches this location
      let selectedMarker = markers.find(
        (marker) =>
          marker.marker.getLatLng().lat === lat &&
          marker.marker.getLatLng().lng === lng
      );

      if (selectedMarker) {
        selectedMarker.marker.setIcon(highlightedIcon);
        selectedMarker.marker.openPopup();
        activeMarker = selectedMarker.marker;
      }
    });
  });

  // Recenter Button
  document
    .getElementById("recenter-btn")
    .addEventListener("click", function () {
      if (activeMarker) {
        activeMarker.closePopup();
      }
      getUserLocation();
    });

  // Initial location setup
  getUserLocation();
});
