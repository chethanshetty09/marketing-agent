"""
main.py — Ayurvedic Clinic Multi-Agent Marketing System
Entry point for running agent crews via CLI.
"""

import json
import argparse
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from crewai import Crew, Task, Process
from agents import (
    create_content_sage,
    create_community_weaver,
    create_reputation_guard,
    create_insight_oracle,
)
from config.settings import settings

console = Console()


def build_agents():
    """Instantiate all 4 agents."""
    return {
        "content_sage": create_content_sage(),
        "community_weaver": create_community_weaver(),
        "reputation_guard": create_reputation_guard(),
        "insight_oracle": create_insight_oracle(),
    }


def build_daily_tasks(agents: dict) -> list[Task]:
    """Build the daily task set."""
    clinic = settings.clinic

    content_task = Task(
        description=(
            f"Create today's social media content for {clinic.name} in {clinic.city}.\n"
            f"1. Check the current Ayurvedic season (Ritu) and align content themes.\n"
            f"2. Research trending wellness topics and local keywords for {clinic.city}.\n"
            f"3. Create 1 Instagram post (caption + hashtags) and 1 Facebook post.\n"
            f"4. If today is Monday or Thursday, draft an 800-word SEO blog article outline.\n"
            f"Clinic specialties: {', '.join(clinic.specialties)}\n"
            f"Output content with suggested posting times in IST."
        ),
        agent=agents["content_sage"],
        expected_output=(
            "JSON with: instagram_post (caption, hashtags, image_description), "
            "facebook_post (text, link), blog_outline (if applicable), "
            "keywords_targeted, suggested_post_times"
        ),
    )

    followup_task = Task(
        description=(
            f"Run the daily patient engagement cycle for {clinic.name}:\n"
            f"1. Draft 3 sample personalized WhatsApp follow-up messages for recent patients.\n"
            f"2. Create a seasonal wellness tip based on current Ritucharya.\n"
            f"3. Review the content from Content Sage and plan distribution strategy.\n"
            f"Ensure all messages are warm, dosha-personalized, and provide genuine value."
        ),
        agent=agents["community_weaver"],
        expected_output=(
            "JSON with: followup_messages (list), seasonal_tip, "
            "distribution_plan, campaign_status"
        ),
        context=[content_task],
    )

    review_task = Task(
        description=(
            f"Perform the reputation monitoring cycle for {clinic.name}:\n"
            f"1. Fetch all recent Google Reviews.\n"
            f"2. Classify each: positive (4-5★), neutral (3★), negative (1-2★).\n"
            f"3. Draft empathetic responses for all unresponded reviews.\n"
            f"4. Flag negative reviews as URGENT.\n"
            f"5. Identify strong testimonial candidates.\n"
            f"Maintain the clinic's compassionate, professional Ayurvedic voice."
        ),
        agent=agents["reputation_guard"],
        expected_output=(
            "JSON with: reviews_analyzed, drafted_responses, "
            "urgent_flags, testimonial_candidates"
        ),
    )

    return [content_task, followup_task, review_task]


def build_weekly_tasks(agents: dict) -> list[Task]:
    """Build the weekly strategy + planning task set."""
    clinic = settings.clinic

    strategy_task = Task(
        description=(
            f"Produce the weekly marketing strategy brief for {clinic.name}:\n"
            f"1. Analyze website traffic patterns and keyword performance.\n"
            f"2. Review the review trends and sentiment patterns.\n"
            f"3. Evaluate content performance (what worked, what didn't).\n"
            f"4. Produce a strategy brief with action items for each agent.\n"
            f"5. Recommend budget allocation changes.\n"
            f"Format as a 5-minute executive summary for the clinic owner."
        ),
        agent=agents["insight_oracle"],
        expected_output=(
            "Strategy brief with: key_metrics, top_content, attention_areas, "
            "action_items_per_agent, budget_recommendations"
        ),
    )

    calendar_task = Task(
        description=(
            f"Plan next week's content calendar for {clinic.name}:\n"
            f"1. Review the strategy brief priorities from Insight Oracle.\n"
            f"2. Align with Ritucharya season and upcoming events.\n"
            f"3. Plan 7 social posts (educational, promotional, engagement mix).\n"
            f"4. Plan 2 SEO blog articles with target keywords.\n"
            f"5. Create 2 Instagram Reel concepts with hooks and scripts.\n"
            f"Specialties: {', '.join(clinic.specialties)}"
        ),
        agent=agents["content_sage"],
        expected_output="7-day content calendar with posts, blogs, and Reel concepts",
        context=[strategy_task],
    )

    campaign_task = Task(
        description=(
            f"Review and optimize all active campaigns for {clinic.name}:\n"
            f"1. Evaluate email and WhatsApp campaign performance.\n"
            f"2. Check referral program results.\n"
            f"3. Plan next week's patient engagement touchpoints.\n"
            f"4. Suggest A/B tests for underperforming campaigns.\n"
            f"Use insights from the strategy brief to prioritize."
        ),
        agent=agents["community_weaver"],
        expected_output="Campaign review with metrics, optimizations, and next week's plan",
        context=[strategy_task],
    )

    return [strategy_task, calendar_task, campaign_task]


def run_crew(tasks: list[Task], agents: dict, mode: str):
    """Execute a crew with the given tasks."""
    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,  # Tasks run in order with context passing
        verbose=True,
        memory=True,
        planning=True,  # CrewAI will create an execution plan first
    )

    console.print(
        Panel(
            f"[bold]Running {mode} workflow[/bold]\n"
            f"Agents: {len(agents)} | Tasks: {len(tasks)}\n"
            f"Clinic: {settings.clinic.name} ({settings.clinic.city})\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M IST')}",
            title="🪷 Ayurvedic Marketing Agents",
            border_style="green",
        )
    )

    result = crew.kickoff()

    # Save result
    output_path = f"outputs/{mode}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    import os
    os.makedirs("outputs", exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(
            {
                "mode": mode,
                "timestamp": datetime.now().isoformat(),
                "clinic": settings.clinic.name,
                "result": str(result),
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    console.print(f"\n[green]✓ Results saved to {output_path}[/green]")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Ayurvedic Clinic Multi-Agent Marketing System"
    )
    parser.add_argument(
        "mode",
        choices=["daily", "weekly", "monthly", "review-scan"],
        help="Which workflow to run",
    )
    args = parser.parse_args()

    agents = build_agents()

    if args.mode == "daily":
        tasks = build_daily_tasks(agents)
        run_crew(tasks, agents, "daily")
    elif args.mode == "weekly":
        tasks = build_weekly_tasks(agents)
        run_crew(tasks, agents, "weekly")
    elif args.mode == "review-scan":
        # Quick single-task run for review monitoring
        task = Task(
            description=(
                f"Scan and respond to all recent Google Reviews for {settings.clinic.name}. "
                f"Draft responses for any unresponded reviews. Flag urgent issues."
            ),
            agent=agents["reputation_guard"],
            expected_output="Review scan results with drafted responses",
        )
        run_crew([task], {"reputation_guard": agents["reputation_guard"]}, "review-scan")
    elif args.mode == "monthly":
        # Monthly includes strategy + full replanning
        tasks = build_weekly_tasks(agents)  # Reuse weekly structure with monthly scope
        tasks[0].description = tasks[0].description.replace("weekly", "monthly (last 30 days)")
        run_crew(tasks, agents, "monthly")


if __name__ == "__main__":
    main()
