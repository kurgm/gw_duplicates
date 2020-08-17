import * as React from "react";

import { List, ListRowRenderer, WindowScroller } from "react-virtualized";

import { Cell } from "./cell";

// [name1, name2, kanrenji1, kanrenji2, num]
export type IDupEntry = [string, string, string | null, string | null, number];

export interface TableProps {
  data: IDupEntry[];
}

export const Table: React.FC<TableProps> = (props: TableProps) => {
  const rowRenderer: ListRowRenderer = React.useCallback(({ index, key, style }) => {
    const entry = props.data[index];
    return (
      <div key={key} style={style} className={`table-row ${index % 2 === 1 ? "" : "gray"}`}>
        <div>{entry[4] + 1}.&nbsp;</div>
        <Cell
          name={entry[0]} related={entry[2]}
          oppositeName={entry[1]} oppositeRelated={entry[3]}
        />
        <Cell
          name={entry[1]} related={entry[3]}
          oppositeName={entry[0]} oppositeRelated={entry[2]}
        />
      </div>
    );
  }, [props.data]);

  return (
    <WindowScroller>
      {({ height, width, isScrolling, onChildScroll, scrollTop }) => (
        <List
          autoHeight
          height={height}
          isScrolling={isScrolling}
          onScroll={onChildScroll}
          rowCount={props.data.length}
          rowHeight={56}
          rowRenderer={rowRenderer}
          scrollTop={scrollTop}
          width={width}
        />
      )}
    </WindowScroller>
  );
};

