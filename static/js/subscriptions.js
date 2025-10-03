document.addEventListener('DOMContentLoaded', function () {
        window.openSubscriptionModal = function (button) {
            const modal = document.getElementById('subscriptionModal');
            const modalContent = document.querySelector('.modal-content');

            if (!modal || !modalContent) {
                console.error('Modal or modal content element not found');
                alert('Failed to open subscription details.');
                return;
            }

            const planName = button.dataset.planName;
            const billingCycle = button.dataset.billingCycle;
            const totalPrice = button.dataset.totalPrice;
            const vcpus = button.dataset.vcpu;
            const ram = button.dataset.ram;
            const osStorage = button.dataset.osStorage;
            const dataStorage = button.dataset.dataStorage;
            const additionalStorage = button.dataset.additionalStorage;
            const additionalVcpus = button.dataset.additionalVcpus;
            const operatingSystem = button.dataset.operatingSystem;
            const status = button.dataset.status;
            const startDate = button.dataset.startDate;
            const endDate = button.dataset.endDate;

            document.getElementById('modalPlanName').textContent = planName || 'N/A';
            document.getElementById('modalBillingCycle').textContent = billingCycle || 'N/A';
            document.getElementById('modalTotalPrice').textContent = totalPrice || 'N/A';
            document.getElementById('modalVCPUs').textContent = vcpus || 'N/A';
            document.getElementById('modalRAM').textContent = ram || 'N/A';
            document.getElementById('modalOSStorage').textContent = osStorage || 'N/A';
            document.getElementById('modalDataStorage').textContent = dataStorage || 'N/A';
            document.getElementById('modalAdditionalStorage').textContent = additionalStorage ? `${additionalStorage} GB` : '0 GB';
            document.getElementById('modalAdditionalVCPUs').textContent = additionalVcpus || '0';
            document.getElementById('modalOperatingSystem').textContent = operatingSystem || 'N/A';
            document.getElementById('modalStatus').textContent = status || 'N/A';
            document.getElementById('modalStartDate').textContent = startDate || 'N/A';
            document.getElementById('modalEndDate').textContent = endDate || 'N/A';

            const statusElement = document.getElementById('modalStatus');
            statusElement.className = 'px-2 inline-flex text-xs leading-5 font-semibold rounded-full';
            if (status && status.toLowerCase() === 'active') {
                statusElement.classList.add('bg-green-100', 'text-green-800');
            } else if (status && status.toLowerCase() === 'pending') {
                statusElement.classList.add('bg-yellow-100', 'text-yellow-800');
            } else {
                statusElement.classList.add('bg-red-100', 'text-red-800');
            }

            modal.classList.remove('hidden');
            modalContent.style.transform = 'scale(1)';
            modalContent.style.opacity = '1';
        };
    });