import {
  isRouteErrorResponse,
  useRouteError,
} from "react-router-dom";

export function AppErrorBoundary() {
  const error = useRouteError();

  console.error("Route error:", error);

  if (isRouteErrorResponse(error)) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-semibold">
          {error.status} {error.statusText}
        </h1>

        <p className="mt-2">
          {typeof error.data === "string"
            ? error.data
            : "Something went wrong."}
        </p>
      </div>
    );
  }

  if (error instanceof Error) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-semibold">
          Application error
        </h1>

        <p className="mt-2 text-red-600">
          {error.message}
        </p>
      </div>
    );
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold">
        Unknown error
      </h1>
    </div>
  );
}