import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ChartCard, StatTile } from "./ChartCard";

describe("ChartCard", () => {
  it("renders its title, optional subtitle, and children", () => {
    render(
      <ChartCard title="Weekly signups" subtitle="By channel">
        <div>chart body</div>
      </ChartCard>,
    );
    expect(screen.getByText("Weekly signups")).toBeInTheDocument();
    expect(screen.getByText("By channel")).toBeInTheDocument();
    expect(screen.getByText("chart body")).toBeInTheDocument();
  });

  it("omits the subtitle element entirely when none is given", () => {
    render(
      <ChartCard title="No subtitle">
        <div>body</div>
      </ChartCard>,
    );
    expect(screen.queryByText("By channel")).not.toBeInTheDocument();
  });
});

describe("StatTile", () => {
  it("renders label, value, and caption", () => {
    render(<StatTile label="Total accounts" value="2,000" caption="all time" />);
    expect(screen.getByText("Total accounts")).toBeInTheDocument();
    expect(screen.getByText("2,000")).toBeInTheDocument();
    expect(screen.getByText("all time")).toBeInTheDocument();
  });
});
