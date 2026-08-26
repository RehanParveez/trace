import { RouterProvider } from "react-router-dom";
import { router } from "./app/router";
import { IdentityBootstrap } from "./modules/identity/components/IdentityBootstrap";

export default function App() {
  return (
    <IdentityBootstrap>
      <RouterProvider router={router} />
    </IdentityBootstrap>
  );
}