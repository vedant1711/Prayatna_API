# hackathon/views.py

from rest_framework import generics
from rest_framework.response import Response
from .models import Team, ApiHitCount
from .serializers import TeamSerializer, ApiHitCountSerializer
import uuid
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.mail import send_mail


class TeamRegistrationView(generics.CreateAPIView):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer

    def perform_create(self, serializer):
        # Customize the data to be saved before creating the Team instance
        team_name = self.request.data.get('team_name', '')
        team_members = self.request.data.get('team_members', [])
        email = self.request.data.get('email', '')
        
        # Generate a UUID for the access key
        access_key = uuid.uuid4()

        # Save the Team instance with the generated access key
        serializer.save(team_name=team_name, team_members=team_members, email=email, access_key=access_key)

        subject = "Prayatna API Access Key"
        message = f"""This is your access key: {access_key}

Each team must integrate the provided API into their project. 
The above Access key must be passed in the Authorization header of the API request in the format "Bearer <access_key>". 
Use the POST method for the specified API URL: http://13.48.136.54:8000/api/api-code/. 
Upon successful request, you will receive an API code in the response, which must be displayed in the footer of your project.
"""
        from_email = "vedantsomani210474@acropolis.in"  # Update with your email
        recipient_list = [email]

        send_mail(subject, message, from_email, recipient_list, fail_silently=False)

        # Return the access key in the response
        return Response({'access_key': str(access_key)})

class TeamInfoView(generics.RetrieveAPIView):    
    serializer_class = TeamSerializer

    def get_object(self):
        access_key = self.request.headers.get('Authorization', '').replace('Bearer ', '')

        if not access_key:
            # Return a meaningful response or raise an appropriate exception
            return Response({'error': 'Access key is required in the Authorization header.'}, status=400)

        try:
            return Team.objects.get(access_key=access_key)
        except Team.DoesNotExist:
            # Handle the case when the team with the provided access key doesn't exist
            return Response({'error': 'Team not found.'}, status=404)


class ApiCodeView(generics.CreateAPIView):
    serializer_class = ApiHitCountSerializer

    def create(self, request, *args, **kwargs):
        access_key = self.request.headers.get('Authorization', '').replace('Bearer ', '')

        if not access_key:
            return Response({'error': 'Access key is required in the Authorization header.'}, status=400)

        team = get_object_or_404(Team, access_key=access_key)
        # Check if the team has an api_code already, if not generate one
        if not team.api_code:
            team.api_code = f"PRAYATNA_{uuid.uuid4().hex}"  # Generate unique api_code
            team.save()
        
        api_hit_count, created = ApiHitCount.objects.get_or_create(team=team)

        # Check if the ApiHitCount was just created or if it needs to be refreshed
        if created or (timezone.now() - api_hit_count.time_refreshed).total_seconds() >= 1800:
            api_hit_count.api_code = team.api_code  # Set api_code to team's api_code
            api_hit_count.time_refreshed = timezone.now()
            api_hit_count.save()

        # Increment the api_hits count
        api_hit_count.api_hits += 1
        api_hit_count.save()

        serializer = self.get_serializer(api_hit_count)
        return Response(serializer.data)