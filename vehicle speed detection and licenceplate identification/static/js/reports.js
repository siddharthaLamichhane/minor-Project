document.addEventListener('DOMContentLoaded', function() {
    const reportForm = document.getElementById('reportForm');
    const dateRange = document.getElementById('dateRange');
    const customDateRange = document.getElementById('customDateRange');
    const startDate = document.getElementById('startDate');
    const endDate = document.getElementById('endDate');
    const loadingAlert = document.getElementById('loadingAlert');
    const errorAlert = document.getElementById('errorAlert');
    const errorMessage = document.getElementById('errorMessage');
    const chartContainer = document.getElementById('chartContainer');
    let chart;

    // Initialize Chart.js
    function initChart(data) {
        if (chart) {
            chart.destroy();
        }

        const ctx = chartContainer.getContext('2d');
        chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.dates,
                datasets: [
                    {
                        label: 'Total Violations',
                        data: data.violations,
                        borderColor: 'rgb(255, 99, 132)',
                        tension: 0.1
                    },
                    {
                        label: 'Average Speed (km/h)',
                        data: data.speeds,
                        borderColor: 'rgb(54, 162, 235)',
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Traffic Violations Analysis'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    // Update table with report data
    function updateTable(details) {
        const tbody = document.querySelector('#reportTable tbody');
        tbody.innerHTML = '';
        
        details.forEach(detail => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${detail.date}</td>
                <td>${detail.total_violations}</td>
                <td>${detail.avg_speed.toFixed(2)} km/h</td>
                <td>${detail.peak_hours}</td>
            `;
            tbody.appendChild(row);
        });
    }

    // Handle date range selection
    dateRange.addEventListener('change', function() {
        customDateRange.style.display = this.value === 'custom' ? 'block' : 'none';
        
        if (this.value !== 'custom') {
            const today = new Date();
            let start = new Date();
            
            switch(this.value) {
                case 'today':
                    start = today;
                    break;
                case 'week':
                    start.setDate(today.getDate() - 7);
                    break;
                case 'month':
                    start.setDate(today.getDate() - 30);
                    break;
            }
            
            startDate.value = start.toISOString().split('T')[0];
            endDate.value = today.toISOString().split('T')[0];
        }
    });

    // Handle form submission
    reportForm.addEventListener('submit', function(e) {
        e.preventDefault();
        loadingAlert.style.display = 'block';
        errorAlert.style.display = 'none';

        const params = new URLSearchParams({
            start_date: startDate.value,
            end_date: endDate.value
        });

        fetch(`/api/report-data?${params}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                initChart(data);
                updateTable(data.details);
                loadingAlert.style.display = 'none';
            })
            .catch(error => {
                loadingAlert.style.display = 'none';
                errorAlert.style.display = 'block';
                const errorMsg = error.response ? error.response.data.error : error.message;
                errorMessage.textContent = errorMsg || 'Failed to connect to the database. Please ensure the database service is running.';
                console.error('Report data fetch error:', error);
            });
    });

    // Handle report download
    document.getElementById('downloadReport').addEventListener('click', function() {
        const params = new URLSearchParams({
            start_date: startDate.value,
            end_date: endDate.value
        });
        window.location.href = `/api/reports/download?${params}`;
    });

    // Set default date range to 'week' and trigger change event
    dateRange.value = 'week';
    dateRange.dispatchEvent(new Event('change'));
    
    // Load initial report
    reportForm.dispatchEvent(new Event('submit'));
});