import axios from "axios";

// В production используем относительный путь через nginx
// В development можно использовать прямой URL к bff-service
const BFF_SERVICE_URL = import.meta.env.VITE_BFF_SERVICE_URL || "/api";

const apiClient = axios.create({
  baseURL: BFF_SERVICE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: false,
});

// Interceptor для обработки ошибок
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API Error:", error);
    return Promise.reject(error);
  }
);

export default apiClient;

