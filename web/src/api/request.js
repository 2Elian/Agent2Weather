import axios from 'axios';

const request = axios.create({
  baseURL: '/api', // Proxy will handle this
  timeout: 300000, // 5 minutes, as generation can take time
});

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    return Promise.reject(error);
  }
);

export const generateWeatherReport = (data) => {
  return request.post('/smw/WeatherReport', data);
};

export const fetchStations = (startDate, endDate) => {
  return request.get('/smw/stations', {
    params: {
      start_date: startDate,
      end_date: endDate,
    },
  });
};
