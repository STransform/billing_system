document.addEventListener('DOMContentLoaded', function () {
    console.log('[DEBUG] Subscriptions page loaded');

    // Open modal with subscription details
    window.openSubscriptionModal = function (button) {
        console.log('[DEBUG] Opening modal for subscription:', button.dataset.subId);
        const modal = document.getElementById('subscriptionModal');
        const modalContent = document.querySelector('.modal-content');

        if (!modal || !modalContent) {
            console.error('[ERROR] Modal or modal content not found');
            alert('Failed to open subscription details: Modal not found.');
            return;
        }

        const data = {
            id: button.dataset.subId,
            planName: button.dataset.planName,
            billingCycle: button.dataset.billingCycle,
            totalPrice: button.dataset.totalPrice,
            vcpus: button.dataset.vcpu,
            ram: button.dataset.ram,
            osStorage: button.dataset.osStorage,
            dataStorage: button.dataset.dataStorage,
            operatingSystem: button.dataset.operatingSystem,
            status: button.dataset.status,
            startDate: button.dataset.startDate,
            endDate: button.dataset.endDate
        };

        console.log('[DEBUG] Modal data:', data);

        const elements = {
            modalPlanName: document.getElementById('modalPlanName'),
            modalBillingCycle: document.getElementById('modalBillingCycle'),
            modalTotalPrice: document.getElementById('modalTotalPrice'),
            modalVCPUs: document.getElementById('modalVCPUs'),
            modalRAM: document.getElementById('modalRAM'),
            modalOSStorage: document.getElementById('modalOSStorage'),
            modalDataStorage: document.getElementById('modalDataStorage'),
            modalOperatingSystem: document.getElementById('modalOperatingSystem'),
            modalStatus: document.getElementById('modalStatus'),
            modalStartDate: document.getElementById('modalStartDate'),
            modalEndDate: document.getElementById('modalEndDate')
        };

        // Check for null elements
        for (const [key, element] of Object.entries(elements)) {
            if (!element) {
                console.error(`[ERROR] Element ${key} not found in DOM`);
                alert(`Failed to open subscription details: Element ${key} not found.`);
                return;
            }
        }

        try {
            elements.modalPlanName.textContent = data.planName || 'N/A';
            elements.modalBillingCycle.textContent = data.billingCycle || 'N/A';
            elements.modalTotalPrice.textContent = data.totalPrice || 'N/A';
            elements.modalVCPUs.textContent = data.vcpus || 'N/A';
            elements.modalRAM.textContent = data.ram || 'N/A';
            elements.modalOSStorage.textContent = data.osStorage || 'N/A';
            elements.modalDataStorage.textContent = data.dataStorage || 'N/A';
            elements.modalOperatingSystem.textContent = data.operatingSystem || 'N/A';
            elements.modalStatus.textContent = data.status || 'N/A';
            elements.modalStartDate.textContent = data.startDate || 'N/A';
            elements.modalEndDate.textContent = data.endDate || 'N/A';

            elements.modalStatus.className = 'px-3 py-1 text-xs font-semibold rounded-full';
            if (data.status && data.status.toLowerCase() === 'active') {
                elements.modalStatus.classList.add('bg-green-100', 'text-green-800');
            } else if (data.status && data.status.toLowerCase() === 'pending') {
                elements.modalStatus.classList.add('bg-yellow-100', 'text-yellow-800');
            } else if (data.status && data.status.toLowerCase() === 'confirmed') {
                elements.modalStatus.classList.add('bg-blue-100', 'text-blue-800');
            } else {
                elements.modalStatus.classList.add('bg-red-100', 'text-red-800');
            }

            modal.classList.remove('hidden');
            modalContent.style.transform = 'scale(1)';
            modalContent.style.opacity = '1';
        } catch (error) {
            console.error('[ERROR] Failed to open modal:', error);
            alert('Failed to open subscription details: ' + error.message);
        }
    };

    // Close modal
    window.closeSubscriptionModal = function () {
        console.log('[DEBUG] Closing modal');
        const modal = document.getElementById('subscriptionModal');
        const modalContent = document.querySelector('.modal-content');

        if (!modal || !modalContent) {
            console.error('[ERROR] Modal or modal content not found');
            alert('Failed to close modal: Modal not found.');
            return;
        }

        try {
            modalContent.style.transform = 'scale(0.95)';
            modalContent.style.opacity = '0';
            setTimeout(() => {
                modal.classList.add('hidden');
                modalContent.style.transform = 'scale(0.95)';
                modalContent.style.opacity = '0';
            }, 300);
        } catch (error) {
            console.error('[ERROR] Failed to close modal:', error);
            alert('Failed to close modal: ' + error.message);
        }
    };

    // Handle form submission with AJAX
    document.querySelectorAll('.confirm-form, .cancel-form').forEach(form => {
        form.addEventListener('submit', function (event) {
            event.preventDefault();
            const subId = this.dataset.subId;
            const action = this.querySelector('input[name="action"]').value;
            const button = this.querySelector('button[type="submit"]');
            const originalButtonText = button.textContent;

            console.log(`[DEBUG] Submitting ${action} for subscription:`, subId);
            console.log('[DEBUG] Form action URL:', this.action);

            button.disabled = true;
            button.textContent = action === 'confirm' ? 'Confirming...' : 'Cancelling...';

            const formData = new FormData(this);
            const url = this.action; // Use form action directly

            fetch(url, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => {
                console.log('[DEBUG] Response status:', response.status);
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('[DEBUG] Response data:', data);
                if (data.success) {
                    const row = document.querySelector(`tr[data-sub-id="${subId}"]`);
                    if (row) {
                        if (action === 'confirm') {
                            const statusBadge = row.querySelector('.status-badge');
                            if (statusBadge) {
                                statusBadge.textContent = 'Confirmed';
                                statusBadge.className = 'status-badge px-3 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800';
                            }

                            const detailsButton = row.querySelector('.details-button');
                            if (detailsButton) {
                                detailsButton.dataset.status = 'Confirmed';
                            }

                            const actionCell = row.querySelector('.action-buttons');
                            actionCell.innerHTML = `
                                <button type="button" class="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-all duration-300 hover:scale-105 focus:ring-4 focus:ring-blue-300 focus:outline-none font-medium text-sm details-button"
                                    data-sub-id="${subId}"
                                    data-plan-name="${detailsButton.dataset.planName}"
                                    data-billing-cycle="${detailsButton.dataset.billingCycle}"
                                    data-total-price="${detailsButton.dataset.totalPrice}"
                                    data-vcpu="${detailsButton.dataset.vcpu}"
                                    data-ram="${detailsButton.dataset.ram}"
                                    data-os-storage="${detailsButton.dataset.osStorage}"
                                    data-data-storage="${detailsButton.dataset.dataStorage}"
                                    data-operating-system="${detailsButton.dataset.operatingSystem}"
                                    data-status="Confirmed"
                                    data-start-date="${detailsButton.dataset.startDate}"
                                    data-end-date="${detailsButton.dataset.endDate}"
                                    onclick="openSubscriptionModal(this)">
                                    <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12h.01M12 12h.01M9 12h.01M12 15h.01M12 9h.01M4 6h16M4 10h16M4 14h16M4 18h16"></path>
                                    </svg>
                                    Details
                                </button>
                            `;
                            console.log(`[DEBUG] Subscription ${subId} confirmed. Status updated to 'confirmed'. Buttons updated.`);
                        } else if (action === 'cancel') {
                            row.remove();
                            console.log(`[DEBUG] Subscription ${subId} cancelled. Row removed.`);
                        }

                        const messageDiv = document.createElement('div');
                        messageDiv.className = 'p-4 rounded-lg text-sm font-medium text-center bg-green-50 text-green-800 border border-green-200 mt-4';
                        messageDiv.textContent = data.message || `Subscription ${action}ed successfully!`;
                        const container = document.querySelector('.container');
                        if (container) {
                            console.log(`[DEBUG] Appending ${action} message to .container`);
                            container.prepend(messageDiv);
                            setTimeout(() => {
                                console.log('[DEBUG] Removing message after 5 seconds');
                                messageDiv.remove();
                            }, 5000);
                        } else {
                            console.error('[ERROR] .container not found for message display');
                            alert(`Subscription ${action}ed, but failed to display message.`);
                        }

                        // Update subscription count
                        const subscriptionCountElement = document.querySelector('.container p.text-sm.text-gray-600.mt-2');
                        if (subscriptionCountElement) {
                            const currentCount = parseInt(subscriptionCountElement.textContent.match(/\d+/)[0]);
                            if (action === 'cancel') {
                                subscriptionCountElement.textContent = `Total Subscriptions: ${currentCount - 1}`;
                            }
                        }
                    } else {
                        console.error('[ERROR] Row not found for subscription:', subId);
                        alert('Action completed, but UI update failed. Please refresh the page.');
                    }
                } else {
                    console.error('[ERROR] Action failed:', data.error);
                    alert(`Failed to ${action} subscription: ${data.error}`);
                    button.disabled = false;
                    button.textContent = originalButtonText;
                }
            })
            .catch(error => {
                console.error(`[ERROR] Failed to ${action} subscription:`, error);
                alert(`Failed to ${action} subscription: ${error.message}`);
                button.disabled = false;
                button.textContent = originalButtonText;
            });
        });
    });
});