# learning/external_platforms.py
import requests
import json
from django.conf import settings
from django.core.cache import cache
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class ExternalLearningPlatform:
    """Base class for external learning platform integrations"""
    
    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CodeSanctuary/1.0',
            'Accept': 'application/json'
        })
    
    def fetch_courses(self, category: str = 'programming', limit: int = 10) -> List[Dict]:
        """Fetch courses from external platform"""
        raise NotImplementedError
    
    def fetch_activity_content(self, external_id: str) -> Optional[Dict]:
        """Fetch specific activity content"""
        raise NotImplementedError
    
    def _cache_key(self, method: str, params: dict) -> str:
        """Generate cache key for API responses"""
        param_str = json.dumps(params, sort_keys=True)
        return f"{self.platform_name}_{method}_{param_str}"


class FreeCodeCampAPI(ExternalLearningPlatform):
    """FreeCodeCamp API integration"""
    
    def __init__(self):
        super().__init__('freecodecamp')
        self.base_url = "https://api.freecodecamp.org/api"
    
    def fetch_courses(self, category='programming', limit=10):
        """Fetch FreeCodeCamp courses"""
        cache_key = self._cache_key('courses', {'category': category, 'limit': limit})
        cached = cache.get(cache_key)
        
        if cached:
            return cached
        
        try:
            # This is a mock - FreeCodeCamp doesn't have a public API for all courses
            # You would need to scrape or use unofficial APIs
            courses = [
                {
                    'title': 'JavaScript Algorithms and Data Structures',
                    'platform': 'FreeCodeCamp',
                    'description': 'Learn JavaScript fundamentals while solving algorithms',
                    'difficulty': 'Beginner to Intermediate',
                    'estimated_time': '300 hours',
                    'url': 'https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures/',
                    'external_id': 'js-algorithms',
                    'language': 'javascript',
                    'is_free': True,
                    'certificate': True,
                },
                {
                    'title': 'Responsive Web Design',
                    'platform': 'FreeCodeCamp',
                    'description': 'Learn HTML, CSS, and responsive design principles',
                    'difficulty': 'Beginner',
                    'estimated_time': '300 hours',
                    'url': 'https://www.freecodecamp.org/learn/responsive-web-design/',
                    'external_id': 'responsive-web',
                    'language': 'html',
                    'is_free': True,
                    'certificate': True,
                },
                {
                    'title': 'Front End Development Libraries',
                    'platform': 'FreeCodeCamp',
                    'description': 'Learn React, Redux, Bootstrap, and more',
                    'difficulty': 'Intermediate',
                    'estimated_time': '300 hours',
                    'url': 'https://www.freecodecamp.org/learn/front-end-development-libraries/',
                    'external_id': 'frontend-libs',
                    'language': 'javascript',
                    'is_free': True,
                    'certificate': True,
                }
            ]
            
            cache.set(cache_key, courses, 3600)  # Cache for 1 hour
            return courses
            
        except Exception as e:
            # Fallback to mock data
            return self._get_mock_courses()
    
    def fetch_activity_content(self, external_id: str):
        """Fetch specific course content"""
        # Mock implementation
        courses = {
            'js-algorithms': {
                'title': 'JavaScript Algorithms and Data Structures',
                'modules': [
                    {'title': 'Basic JavaScript', 'lessons': 110},
                    {'title': 'ES6', 'lessons': 31},
                    {'title': 'Regular Expressions', 'lessons': 33},
                    {'title': 'Debugging', 'lessons': 12},
                    {'title': 'Basic Data Structures', 'lessons': 20},
                    {'title': 'Basic Algorithm Scripting', 'lessons': 16},
                    {'title': 'Object Oriented Programming', 'lessons': 26},
                    {'title': 'Functional Programming', 'lessons': 24},
                    {'title': 'Intermediate Algorithm Scripting', 'lessons': 21},
                    {'title': 'JavaScript Algorithms and Data Structures Projects', 'lessons': 5},
                ],
                'total_lessons': 298,
                'description': 'Master JavaScript by solving algorithms and building projects'
            }
        }
        return courses.get(external_id, None)
    
    def _get_mock_courses(self):
        """Return mock courses for fallback"""
        return [
            {
                'title': 'Scientific Computing with Python',
                'platform': 'FreeCodeCamp',
                'url': 'https://www.freecodecamp.org/learn/scientific-computing-with-python/',
                'difficulty': 'Intermediate'
            },
            {
                'title': 'Data Analysis with Python',
                'platform': 'FreeCodeCamp',
                'url': 'https://www.freecodecamp.org/learn/data-analysis-with-python/',
                'difficulty': 'Intermediate'
            }
        ]


class UdemyAPI(ExternalLearningPlatform):
    """Udemy API integration (requires API credentials)"""
    
    def __init__(self):
        super().__init__('udemy')
        self.base_url = "https://www.udemy.com/api-2.0"
        self.client_id = getattr(settings, 'UDEMY_CLIENT_ID', '')
        self.client_secret = getattr(settings, 'UDEMY_CLIENT_SECRET', '')
    
    def fetch_courses(self, category='development', limit=10):
        """Fetch Udemy courses"""
        if not self.client_id or not self.client_secret:
            return self._get_mock_udemy_courses()
        
        cache_key = self._cache_key('courses', {'category': category, 'limit': limit})
        cached = cache.get(cache_key)
        
        if cached:
            return cached
        
        try:
            # Udemy API requires authentication
            auth = (self.client_id, self.client_secret)
            params = {
                'page': 1,
                'page_size': limit,
                'category': category,
                'ordering': 'highest-rated'
            }
            
            response = self.session.get(
                f"{self.base_url}/courses/",
                auth=auth,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                courses = []
                for course in data.get('results', []):
                    courses.append({
                        'title': course.get('title'),
                        'platform': 'Udemy',
                        'description': course.get('headline', ''),
                        'difficulty': self._map_difficulty(course.get('instructional_level', '')),
                        'estimated_time': f"{course.get('content_info', '').split(' ')[0] if course.get('content_info') else 'Unknown'} hours",
                        'url': course.get('url'),
                        'external_id': str(course.get('id')),
                        'language': 'Multiple',
                        'is_free': course.get('is_paid', True) == False,
                        'rating': course.get('avg_rating', 0),
                        'students': course.get('num_subscribers', 0),
                        'price': course.get('price', 'Paid'),
                    })
                
                cache.set(cache_key, courses, 7200)  # Cache for 2 hours
                return courses
            else:
                return self._get_mock_udemy_courses()
                
        except Exception as e:
            return self._get_mock_udemy_courses()
    
    def _get_mock_udemy_courses(self):
        """Mock Udemy courses for when API is unavailable"""
        return [
            {
                'title': 'The Complete Python Bootcamp From Zero to Hero in Python',
                'platform': 'Udemy',
                'description': 'Learn Python like a Professional! Start from the basics and go all the way to creating your own applications and games!',
                'difficulty': 'Beginner',
                'estimated_time': '22 hours',
                'url': 'https://www.udemy.com/course/complete-python-bootcamp/',
                'external_id': 'udemy_python_bootcamp',
                'language': 'python',
                'is_free': False,
                'rating': 4.6,
                'students': '1,500,000+',
            },
            {
                'title': 'The Web Developer Bootcamp 2025',
                'platform': 'Udemy',
                'description': 'COMPLETELY REDONE - The only course you need to learn web development - HTML, CSS, JS, Node, and More!',
                'difficulty': 'Beginner',
                'estimated_time': '63.5 hours',
                'url': 'https://www.udemy.com/course/the-web-developer-bootcamp/',
                'external_id': 'udemy_web_bootcamp',
                'language': 'javascript',
                'is_free': False,
                'rating': 4.7,
                'students': '800,000+',
            }
        ]
    
    def _map_difficulty(self, level: str) -> str:
        """Map Udemy instructional level to our difficulty levels"""
        mapping = {
            'Beginner Level': 'Beginner',
            'Intermediate Level': 'Intermediate',
            'Expert Level': 'Advanced',
            'All Levels': 'All Levels'
        }
        return mapping.get(level, 'All Levels')


class CourseraAPI(ExternalLearningPlatform):
    """Coursera API integration"""
    
    def __init__(self):
        super().__init__('coursera')
        self.base_url = "https://api.coursera.org/api/courses.v1"
    
    def fetch_courses(self, category='computer-science', limit=10):
        """Fetch Coursera courses"""
        cache_key = self._cache_key('courses', {'category': category, 'limit': limit})
        cached = cache.get(cache_key)
        
        if cached:
            return cached
        
        try:
            # Mock data - Coursera API requires special access
            courses = [
                {
                    'title': 'Python for Everybody',
                    'platform': 'Coursera',
                    'description': 'Learn to Program and Analyze Data with Python. Develop programs to gather, clean, analyze, and visualize data.',
                    'difficulty': 'Beginner',
                    'estimated_time': '8 months',
                    'url': 'https://www.coursera.org/specializations/python',
                    'external_id': 'coursera_python_everybody',
                    'language': 'python',
                    'is_free': True,  # Audit option is free
                    'university': 'University of Michigan',
                    'enrollment': '1.8M',
                },
                {
                    'title': 'Machine Learning',
                    'platform': 'Coursera',
                    'description': 'Master the essentials of machine learning and AI',
                    'difficulty': 'Intermediate',
                    'estimated_time': '4 months',
                    'url': 'https://www.coursera.org/learn/machine-learning',
                    'external_id': 'coursera_ml',
                    'language': 'python',
                    'is_free': True,
                    'university': 'Stanford University',
                    'enrollment': '4.7M',
                }
            ]
            
            cache.set(cache_key, courses, 7200)
            return courses
            
        except Exception as e:
            return self._get_mock_coursera_courses()
    
    def _get_mock_coursera_courses(self):
        """Mock Coursera courses"""
        return [
            {
                'title': 'Google IT Automation with Python',
                'platform': 'Coursera',
                'url': 'https://www.coursera.org/professional-certificates/google-it-automation',
                'difficulty': 'Beginner'
            }
        ]


class LearningPlatformAggregator:
    """Aggregates content from multiple learning platforms"""
    
    def __init__(self):
        self.platforms = {
            'freecodecamp': FreeCodeCampAPI(),
            'udemy': UdemyAPI(),
            'coursera': CourseraAPI(),
        }
    
    def get_all_courses(self, category='programming', limit_per_platform=5):
        """Get courses from all platforms"""
        all_courses = []
        
        for platform_name, platform in self.platforms.items():
            try:
                courses = platform.fetch_courses(category=category, limit=limit_per_platform)
                all_courses.extend(courses)
            except Exception as e:
                # Skip platforms that fail
                continue
        
        # Sort by platform, then by title
        all_courses.sort(key=lambda x: (x['platform'], x['title']))
        return all_courses
    
    def get_platform_courses(self, platform_name: str, **kwargs):
        """Get courses from specific platform"""
        platform = self.platforms.get(platform_name)
        if platform:
            return platform.fetch_courses(**kwargs)
        return []
    
    def search_courses(self, query: str, category: str = None):
        """Search courses across all platforms"""
        all_courses = self.get_all_courses(category=category if category else 'programming')
        
        # Simple search - in production you'd use more sophisticated search
        query_lower = query.lower()
        results = []
        
        for course in all_courses:
            if (query_lower in course['title'].lower() or 
                query_lower in course.get('description', '').lower() or
                query_lower in course.get('language', '').lower()):
                results.append(course)
        
        return results


# Singleton instance
platform_aggregator = LearningPlatformAggregator()