# 📡 Network Monitoring Dashboard

A real-time dashboard built with **Dash**, **Plotly**, and **MySQL**, which provides:

* A **sunburst chart** visualizing active devices by subnet.
* A **bandwidth monitoring graph** tracking sent and received data in Mbps.
* **Automatic updates** every 2–3 minutes.
* A **network connectivity error modal** to alert users of any disconnection.

---

## 🚀 Features

* 🔍 **Subnet Scanner**: Periodically scans all predefined subnets and visualizes active devices per department.
* 📈 **Real-Time Bandwidth Graph**: Tracks and displays system-wide upload and download bandwidth in Mbps.
* 💾 **MySQL Database Integration**: Stores bandwidth logs for historical analysis.
* ⏱️ **Live Updates**: Updates graphs every 2–3 minutes using Dash's `dcc.Interval`.
* ⚠️ **Network Error Modal**: Displays a warning modal if connectivity is lost or data retrieval fails.

---

## 🛠️ Tech Stack

* **Frontend**: Dash (Plotly), HTML/CSS, Bootstrap Components
* **Backend**: Python (psutil, threading, concurrent.futures, subprocess)
* **Database**: MySQL
* **Libraries**: `psutil`, `mysql-connector-python`, `plotly`, `dash`, `dash-bootstrap-components`, `pandas`

---

## ⚙️ Setup Instructions

### 🔧 Prerequisites

* Python 3.x installed
* MySQL Server running
* MySQL user with credentials (default: `root`/`bharathi`)
* Required Python packages:

  ```bash
  pip install dash dash-bootstrap-components plotly pandas psutil mysql-connector-python
  ```

### 🧩 Database Setup

1. Create a database named:

   ```sql
   CREATE DATABASE network_monitor;
   ```

2. Run the app — it will automatically create the required table:

   ```sql
   CREATE TABLE bandwidth_data (
     id INT AUTO_INCREMENT PRIMARY KEY,
     timestamp DATETIME NOT NULL,
     bytes_sent BIGINT NOT NULL,
     bytes_recv BIGINT NOT NULL
   );
   ```

---

## ▶️ Running the App

```bash
python monitoringsystem.py
```

Once running, open your browser and navigate to:

```
http://127.0.0.1:8050/
```

---

## 🗺️ Project Structure

```
📁 network-monitor/
│
├── monitoringsystem.py                  # Main Dash application
└── README.md               # You're reading it!
```

---

## 📊 Sunburst Chart: Active Devices by Subnet

* Scans IPs like `10.53.2.*`, `10.53.3.*`... for device activity using `ping`.
* Displays subnet-wise active device count grouped by department.
* Updated every 3 minutes.
* Keeps last valid chart visible even on error.

---

## 📡 Bandwidth Monitor Graph

* Fetches system bandwidth usage using `psutil.net_io_counters()`.
* Stores real-time logs into `bandwidth_data` table every 2 minutes.
* Displays past 2 hours of data on a dynamic line chart with `Plotly`.

---

## ❗ Error Modal

If there's a network disconnection:

* Connectivity check with `https://www.google.com`
* Modal alert is shown with a dismiss button
* Sunburst chart uses the last known figure to ensure the UI remains populated

---

## 🧪 Testing & Debugging

* Use `print()` logs for:

  * Stored bandwidth data
  * Database fetches
* Test subnet scanning manually using `ping` command
* Inspect `timestamps`, `sent_data`, and `recv_data` for plot validation

---

## 💡 Future Enhancements

* Add user authentication for secure access
* Enable custom time-range selection for bandwidth reports
* Export reports as CSV/PDF
* Set bandwidth or device count alerts via email

---

## 👤 Author

**C Bharathi**
Tech enthusiast and builder of real-time dashboards

---

## 📝 License

Apache license


