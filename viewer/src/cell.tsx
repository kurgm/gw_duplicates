import * as React from "react";

const uxxxx2char = (uxxxx: string) => {
  const cp = parseInt(uxxxx.substring(1), 16);
  if (cp < 0x10000) {
    return String.fromCharCode(cp);
  }
  const cp1 = 0xD800 | ((cp - 0x10000) >> 10);
  const cp2 = 0xDC00 | ((cp - 0x10000) & 0x3ff);
  return String.fromCharCode(cp1, cp2);
};

const qs = (obj: { [key: string]: string }) => {
  return Object.keys(obj).map((key) => (
    encodeURIComponent(key) + "=" + encodeURIComponent(obj[key])
  )).join("&");
};

export interface CellProps {
  name: string;
  related: string | null;
  oppositeName: string;
  oppositeRelated: string | null;
}

export const Cell: React.FC<CellProps> = (props: CellProps) => {
  const url = `https://glyphwiki.org/wiki/${props.name}`;
  return (
    <div>
      <a href={url} target="_new">
        <img
          src={`https://glyphwiki.org/glyph/${props.name}.svg`}
          alt={props.name}
          className="thumb"
        />
      </a>
      <a href={url} target="_new">{props.name}</a>
      {props.related && `(${uxxxx2char(props.related)})`}
      <div className="filler"></div>
      <a
        href={url + "?" + qs({
          action: "preview",
          related: props.related || "u3013",
          summary: props.oppositeName,
          textbox: `[[${props.oppositeName}]]`,
        })}
        className="edit-link"
        target="_new"
        title="このグリフを、もう片方のグリフを参照するエイリアスに変更します。"
      >
        エイリアス化
      </a>
      &nbsp;
      <a
        href={url + "?" + qs({
          action: "preview",
          summary: props.oppositeName,
          textbox: "0:0:0:0",
        })}
        className="edit-link"
        target="_new"
        title="このグリフを白紙化します。"
      >
        白紙化
      </a>
    </div>
  );
};
