import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/NotFound";
import { Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import Home from "./pages/Home";
import CreateSession from "./pages/CreateSession";
import SessionDetail from "./pages/SessionDetail";
import GradingDashboard from "./pages/GradingDashboard";
import ResultDetail from "./pages/ResultDetail";
import GradeStudentPage from "./pages/GradeStudentPage";

function Router() {
  return (
    <Switch>
      <Route path="/" component={Home} />
      <Route path="/create-session" component={CreateSession} />
      <Route path="/session/:sessionId">
        {(params) => <SessionDetail sessionId={parseInt(params.sessionId)} />}
      </Route>
      <Route path="/dashboard/:sessionId">
        {(params) => <GradingDashboard sessionId={parseInt(params.sessionId)} />}
      </Route>
      <Route path="/result/:sessionId/:studentAnswerId">
        {(params) => (
          <ResultDetail
            sessionId={parseInt(params.sessionId)}
            studentAnswerId={parseInt(params.studentAnswerId)}
          />
        )}
      </Route>
      <Route path="/grade/:sessionId/:studentAnswerId">
        {(params) => (
          <GradeStudentPage
            sessionId={parseInt(params.sessionId)}
            studentAnswerId={parseInt(params.studentAnswerId)}
            studentName=""
          />
        )}
      </Route>
      <Route path="/404" component={NotFound} />
      <Route component={NotFound} />
    </Switch>
  );
}

// NOTE: About Theme
// - First choose a default theme according to your design style (dark or light bg), than change color palette in index.css
//   to keep consistent foreground/background color across components
// - If you want to make theme switchable, pass `switchable` ThemeProvider and use `useTheme` hook

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider
        defaultTheme="light"
        // switchable
      >
        <TooltipProvider>
          <Toaster />
          <Router />
        </TooltipProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
