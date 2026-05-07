// Toggle habit completion
async function toggleHabit(habitId) {
    try {
        const response = await fetch('/toggle_habit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ habit_id: habitId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Update button appearance
            const button = document.querySelector(`button[onclick="toggleHabit(${habitId})"]`);
            button.innerHTML = data.completed ? '✅' : '⭕';
            
            // Update streaks display
            const habitCard = button.closest('.habit-card');
            const streakCurrent = habitCard.querySelector('.streak-current .streak-count');
            const streakLongest = habitCard.querySelector('.streak-longest .streak-count');
            streakCurrent.textContent = data.current_streak;
            streakLongest.textContent = data.longest_streak;
            
            // Show brief animation
            button.style.transform = 'scale(1.3)';
            setTimeout(() => {
                button.style.transform = 'scale(1)';
            }, 200);
        } else {
            alert('Error updating habit: ' + data.error);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to update habit. Please try again.');
    }
}

// Delete habit
async function deleteHabit(habitId) {
    if (!confirm('Are you sure you want to delete this habit? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch('/delete_habit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ habit_id: habitId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Remove habit card with animation
            const habitCard = document.querySelector(`button[onclick="deleteHabit(${habitId})"]`).closest('.habit-card');
            habitCard.style.opacity = '0';
            habitCard.style.transform = 'translateX(100px)';
            habitCard.style.transition = 'all 0.3s ease';
            
            setTimeout(() => {
                habitCard.remove();
                
                // Reload page if no habits left
                const remainingCards = document.querySelectorAll('.habit-card');
                if (remainingCards.length === 0) {
                    location.reload();
                }
            }, 300);
        } else {
            alert('Error deleting habit: ' + data.error);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to delete habit. Please try again.');
    }
}

// Habit statistics (optional, for detail views)
async function loadHabitStats(habitId) {
    try {
        const response = await fetch(`/stats/${habitId}`);
        const data = await response.json();
        
        if (data.success) {
            console.log(`Stats for ${data.name}:`, data);
            // You can use this data to create charts or additional displays
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Add smooth scroll behavior
document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.5s ease';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });
    
    // Add keyboard shortcut for toggling habits (optional)
    document.addEventListener('keydown', function(e) {
        if (e.key === ' ' && e.target === document.body) {
            e.preventDefault();
            const firstToggleBtn = document.querySelector('.btn-toggle');
            if (firstToggleBtn) {
                firstToggleBtn.click();
            }
        }
    });
});
