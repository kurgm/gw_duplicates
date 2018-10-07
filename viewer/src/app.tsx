import * as React from "react";
import * as ReactDOM from "react-dom";

import axios from "axios";

import { IDupEntry, Table } from "./table";

interface IAppState {
  data: IDupEntry[];
  query: RegExp | null;
  timestamp: string | null;
}

class App extends React.Component<{}, IAppState> {
  public state: IAppState = {
    data: [],
    query: null,
    timestamp: null,
  };

  private searchInput = React.createRef<HTMLInputElement>();

  public render() {
    if (!this.state.timestamp) {
      return (
        <div style={{
          color: "gray",
          fontSize: "24px",
          textAlign: "center",
        }}>
          読み込み中...
        </div>
      );
    }
    const shownData = (!this.state.query)
      ? this.state.data
      : this.state.data.filter((entry) => {
        if (this.state.query!.test(entry[0])) {
          return true;
        }
        if (this.state.query!.test(entry[1])) {
          return true;
        }
        if (entry[2] && this.state.query!.test(entry[2]!)) {
          return true;
        }
        if (entry[3] && this.state.query!.test(entry[3]!)) {
          return true;
        }
        return false;
      });
    return (
      <div>
        <div className="lr-margin">
          <small>
            {this.state.timestamp} の dump より生成（全 {this.state.data.length} 件{
              this.state.data.length !== shownData.length &&
                `中 ${shownData.length} 件を表示`
            }）
            </small>
        </div>
        <div className="search">
          <input
            type="text"
            onChange={this.handleSearchChange}
            placeholder="検索（グリフ名または漢字）"
            ref={this.searchInput}
          />
        </div>
        <Table data={shownData} />
      </div>
    );
  }

  public componentDidMount() {
    axios.get("./duplicates.json").then((json) => {
      const data: IDupEntry[] = json.data.buhin.concat(json.data.kaku);
      data.forEach((row, i) => { row[4] = i; });
      this.setState({
        data,
        timestamp: new Date(json.data.timestamp * 1000).toLocaleString(),
      });
    });
  }

  private handleSearchChange = () => {
    const obj = this.searchInput.current!.value;
    let query;
    if (obj === "") {
      query = null;
    } else if (/^[^\x00-\xFF]+$/.test(obj)) {
      query = new RegExp("(?:^|-)" + text2uxxx(obj) + "(?:-|$)");
    } else {
      try {
        query = new RegExp(obj);
      } catch (e) {
        this.searchInput.current!.setCustomValidity("正規表現エラー: " + e.message);
        return;
      }
    }
    this.searchInput.current!.setCustomValidity("");
    this.setState({ query });
  }
}

const text2uxxx = (str: string) => {
  const cp = [];
  for (let i = 0; i < str.length; i++) {
    const x = str.charCodeAt(i);
    if (0xD800 <= x && x <= 0xDBFF) {
      const y = str.charCodeAt(++i);
      if (!isNaN(y)) {
        // tslint:disable-next-line:no-bitwise
        cp.push(0x10000 + (((x & 0x3FF) << 10) | (y & 0x3FF)));
        continue;
      }
    }
    cp.push(x);
  }
  return cp.map((c) => "u" + ("000" + c.toString(16)).slice(-4)).join("-");
};

ReactDOM.render(<App />, document.getElementById("app"));
