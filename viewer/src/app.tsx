import * as React from "react";
import { createRoot } from "react-dom/client";

import { IDupEntry, Table } from "./table";

const jsonUrl = process.env.RESULT_JSON_URL!;

const text2uxxx = (str: string) => {
  return [...str]
    .map((c) => {
      const code = c.codePointAt(0)!;
      return `u${code.toString(16).padStart(4, "0")}`;
    })
    .join("-");
};

const App: React.FC<Record<string, never>> = () => {
  const [{ data, timestamp }, setDataTimestamp] = React.useState<{
    data: IDupEntry[];
    timestamp: string | null;
  }>({
    data: [],
    timestamp: null,
  });
  const [query, setQuery] = React.useState<RegExp | null>(null);
  const [errored, setErrored] = React.useState(false);

  React.useEffect(() => {
    fetch(jsonUrl).then((response) => {
      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }
      return response.json();
    }).then((jsonData: {
      buhin: IDupEntry[];
      kaku: IDupEntry[];
      timestamp: number;
    }) => {
      const data = jsonData.buhin.concat(jsonData.kaku);
      data.forEach((row, i) => { row[4] = i; });
      setDataTimestamp({
        data,
        timestamp: new Date(jsonData.timestamp * 1000).toLocaleString(),
      });
    }).catch(() => {
      setErrored(true);
    });
  }, []);

  const handleSearchChange = React.useCallback<React.ChangeEventHandler<HTMLInputElement>>((evt) => {
    const inputElem = evt.currentTarget;
    const obj = inputElem.value;
    let query;
    if (obj === "") {
      query = null;
    } else if (/^[^\0-\xFF]+$/.test(obj)) {
      query = new RegExp("(?:^|-)" + text2uxxx(obj) + "(?:-|$)");
    } else {
      try {
        query = new RegExp(obj);
      } catch (e) {
        if (e instanceof SyntaxError) {
          inputElem.setCustomValidity(`正規表現エラー: ${e.message}`);
        }
        return;
      }
    }
    inputElem.setCustomValidity("");
    setQuery(query);
  }, []);
  if (!timestamp) {
    return (
      <div style={{
        color: "gray",
        fontSize: "24px",
        textAlign: "center",
      }}>
        {errored ? "読み込みエラー" : "読み込み中..."}
      </div>
    );
  }
  const shownData = (!query)
    ? data
    : data.filter((entry) => {
      if (query.test(entry[0])) {
        return true;
      }
      if (query.test(entry[1])) {
        return true;
      }
      if (entry[2] && query.test(entry[2])) {
        return true;
      }
      if (entry[3] && query.test(entry[3])) {
        return true;
      }
      return false;
    });
  return (
    <div>
      <div className="lr-margin">
        <small>
          {timestamp} の dump より生成（全 {data.length} 件{
            data.length !== shownData.length &&
            `中 ${shownData.length} 件を表示`
          }）
        </small>
      </div>
      <div className="search">
        <input
          type="text"
          onChange={handleSearchChange}
          placeholder="検索（グリフ名または漢字）"
        />
      </div>
      <Table data={shownData} />
    </div>
  );
};

createRoot(document.getElementById("app")!).render(<App />);
