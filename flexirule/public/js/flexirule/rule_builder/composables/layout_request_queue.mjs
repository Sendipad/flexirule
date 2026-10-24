/**
 * Serialize asynchronous requests while allowing pending requests to coalesce.
 *
 * A graph layout is a snapshot operation: when multiple requests arrive during
 * an active layout, only the newest pending request needs to execute. Every
 * caller waiting on a coalesced request settles when that newest request ends.
 */
export function createLatestRequestQueue() {
	let isDraining = false;
	let pendingRequest = null;

	async function drain() {
		while (pendingRequest) {
			const request = pendingRequest;
			pendingRequest = null;

			try {
				const result = await request.task();
				request.waiters.forEach(({ resolve }) => resolve(result));
			} catch (error) {
				request.waiters.forEach(({ reject }) => reject(error));
			}
		}

		isDraining = false;
		// There is no await between the empty check and clearing the flag, but
		// keep this guard explicit so future changes cannot strand a request.
		if (pendingRequest) {
			isDraining = true;
			void drain();
		}
	}

	return function enqueue(task) {
		if (typeof task !== "function") {
			return Promise.reject(new TypeError("A queued request must be a function."));
		}

		return new Promise((resolve, reject) => {
			const waiter = { resolve, reject };

			if (pendingRequest) {
				// Coalesce queued work to the latest state/direction, but settle
				// every caller that was waiting for a queued layout to finish.
				pendingRequest.task = task;
				pendingRequest.waiters.push(waiter);
			} else {
				pendingRequest = { task, waiters: [waiter] };
			}

			if (!isDraining) {
				isDraining = true;
				void drain();
			}
		});
	};
}
