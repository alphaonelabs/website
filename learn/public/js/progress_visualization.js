document.addEventListener("DOMContentLoaded", function() {
    const progressLabels = JSON.parse(progressDates);
    const sessionsData = JSON.parse(sessionsCompleted);
    const courseData = JSON.parse(coursesJson);

    const coursesPdfData = courseData;
    const totalCourses = totalCoursesCount;
    const coursesCompleted = coursesCompletedCount;
    const topicsMastered = topicsMasteredCount;
    const averageAttendance = averageAttendancePercentage;

    const progressCtx = document.getElementById('progressChart').getContext('2d');
    const progressChart = new Chart(progressCtx, {
        type: 'line',
        data: {
            labels: progressLabels,
            datasets: courseData.map((course, index) => ({
                label: course.title,
                data: course.progress_over_time,
                borderColor: `rgba(${course.color}, 1)`,
                backgroundColor: `rgba(${course.color}, 0.2)`,
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }))
        },
        options: {
            responsive: true,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const datasetIndex = context.datasetIndex;
                            const dataIndex = context.dataIndex;
                            const courseName = context.dataset.label;
                            const progressValue = context.raw;

                            const sessionCount = sessionsData[datasetIndex] ?
                                (sessionsData[datasetIndex][dataIndex] || 0) : 0;

                            return `${courseName}: ${progressValue}% (${sessionCount} sessions completed)`;
                        }
                    }
                },
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Course Progress Over Time'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Completion Percentage'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Date'
                    }
                }
            }
        }
    });

    // Generate PDF Report
    document.getElementById("shareProgress").addEventListener("click", function() {
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();

        doc.setFontSize(22);
        doc.text("Learning Progress Report", 105, 20, {
            align: 'center'
        });
        doc.setFontSize(12);
        doc.text(`Generated on: ${new Date().toLocaleDateString()}`, 105, 30, {
            align: 'center'
        });

        doc.setFontSize(16);
        doc.text("Overview", 20, 50);
        doc.setFontSize(12);
        doc.text(`Total Courses: ${totalCourses}`, 20, 60);
        doc.text(`Courses Completed: ${coursesCompleted}`, 20, 70);
        doc.text(`Topics Mastered: ${topicsMastered}`, 20, 80);
        doc.text(`Average Attendance: ${averageAttendance}%`, 20, 90);

        doc.setFontSize(16);
        doc.text("Progress Over Time", 20, 110);

        html2canvas(document.getElementById("progressChart")).then(canvas => {
            const imgData = canvas.toDataURL("image/png");
            doc.addImage(imgData, "PNG", 20, 120, 170, 80);

            doc.setFontSize(16);
            doc.text("Course Progress", 20, 210);

            let y = 220;

            coursesPdfData.forEach(course => {
                doc.setFontSize(12);
                doc.text(course.title, 20, y);
                y += 10;

                doc.setDrawColor(200, 200, 200);
                doc.setFillColor(200, 200, 200);
                doc.rect(20, y, 150, 5, 'F');

                const [r, g, b] = course.color.split(',').map(val => parseInt(val.trim()));
                doc.setFillColor(r, g, b);

                doc.rect(20, y, 150 * (course.progress / 100), 5, 'F');

                doc.text(`${course.progress}%`, 175, y + 4);
                y += 15;
            });

            doc.save("Learning_Progress_Report.pdf");
        });
    });

    // Share as Image
    document.getElementById("shareImage").addEventListener("click", function() {
        html2canvas(document.querySelector(".container")).then(canvas => {
            const link = document.createElement('a');
            link.download = 'learning_progress.png';
            link.href = canvas.toDataURL("image/png");
            link.click();
        });
    });
});
