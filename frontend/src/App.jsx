import { useState } from 'react';
import Home from './pages/Home.jsx';
import Upload from './pages/Upload.jsx';
import Results from './pages/Results.jsx';

export default function App() {
  const [view, setView] = useState('home');
  const [results, setResults] = useState([]);
  const [uploadData, setUploadData] = useState(null);

  const navigate = (to) => setView(to);

  const handleResults = (res, upload) => {
    setResults(res);
    setUploadData(upload);
    setView('results');
  };

  if (view === 'results') {
    return (
      <Results
        results={results}
        uploadData={uploadData}
        onNavigate={navigate}
      />
    );
  }

  if (view === 'upload') {
    return (
      <Upload
        onNavigate={navigate}
        onResults={handleResults}
      />
    );
  }

  return <Home onNavigate={navigate} />;
}
