module.exports = (on, config) => {
	try {
		require("@cypress/code-coverage/task")(on, config);
	} catch (e) {
		// coverage not installed
	}
	return config;
};
