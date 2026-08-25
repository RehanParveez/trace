import { createBrowserRouter } from "react-router-dom";
import { HomePage } from "../modules/home/HomePage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <HomePage />,
  },
]);