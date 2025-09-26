export default function handler(req, res) {
  res.status(200).json([
    { city: "New York", temp: "25°C", condition: "Sunny" },
    { city: "London", temp: "18°C", condition: "Cloudy" },
    { city: "Tokyo", temp: "30°C", condition: "Rainy" }
  ]);
}
