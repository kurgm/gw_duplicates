import * as React from "react";

import { useWindowVirtualizer } from "@tanstack/react-virtual";

import { Cell } from "./cell";

// [name1, name2, kanrenji1, kanrenji2, num]
export type IDupEntry = [string, string, string | null, string | null, number];

export interface TableProps {
  data: IDupEntry[];
}

export const Table: React.FC<TableProps> = (props: TableProps) => {
  const parentRef = React.useRef<HTMLDivElement>(null);

  const getItemKey = React.useCallback(
    (index: number) => props.data[index][4],
    [props.data]
  );

  const virtualizer = useWindowVirtualizer({
    count: props.data.length,
    estimateSize: () => 56,
    scrollMargin: parentRef.current?.offsetTop ?? 0,
    getItemKey,
    overscan: 10,
  });

  return (
    <div
      ref={parentRef}
      style={{
        position: "relative",
        width: "100%",
        height: virtualizer.getTotalSize(),
      }}
    >
      {virtualizer.getVirtualItems().map((item) => {
        const entry = props.data[item.index];
        return (
          <div
            key={item.key}
            data-index={item.index}
            ref={virtualizer.measureElement}
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              transform: `translateY(${
                item.start - virtualizer.options.scrollMargin
              }px)`,
            }}
            className={`table-row ${item.index % 2 === 1 ? "" : "gray"}`}
          >
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
      })}
    </div>
  );
};
