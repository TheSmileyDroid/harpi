import { Configuration, DefaultApi } from './api'; // Import from the generated folder

// Configure your backend URL
const config = new Configuration({
	basePath: ''
});

// Initialize the API (OpenAPI typically puts un-tagged routes in DefaultApi)
export const api = new DefaultApi(config);
