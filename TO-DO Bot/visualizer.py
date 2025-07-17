import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import logging

logger = logging.getLogger(__name__)

class StatsVisualizer:
    @staticmethod
    def generate_stats_plot(data, user_id):
        try:
            if not data:
                logger.error(f"No data provided for user {user_id}")
                return None
            categories = {}
            for category, completed, count in data:
                if category not in categories:
                    categories[category] = {'completed': 0, 'total': 0}
                categories[category]['total'] += count
                if completed:
                    categories[category]['completed'] += count
            if not categories:
                logger.error(f"No valid stats data for user {user_id}")
                return None
            plt.figure(figsize=(8, 6))
            cat_names = list(categories.keys())
            progress = [categories[cat]['completed'] / categories[cat]['total'] * 100 for cat in cat_names]
            plt.bar(cat_names, progress, color='skyblue')
            plt.xlabel('Категории')
            plt.ylabel('Процент выполнения (%)')
            plt.title('Статистика выполнения задач')
            plt.xticks(rotation=45)
            plot_file = f'stats_{user_id}.png'
            plt.savefig(plot_file, bbox_inches='tight')
            plt.close()
            if not os.path.exists(plot_file):
                logger.error(f"Plot file {plot_file} was not created for user {user_id}")
                return None
            logger.info(f"Generated stats plot for user {user_id}: {plot_file}")
            return plot_file
        except Exception as e:
            logger.error(f"Failed to generate stats plot for user {user_id}: {e}")
            return None

visualizer_instance = StatsVisualizer()

def generate_stats_plot(data, user_id):
    return visualizer_instance.generate_stats_plot(data, user_id)