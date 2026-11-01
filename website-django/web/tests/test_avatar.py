from python_avatars import Avatar, AvatarStyle

# Create a simple avatar
avatar = Avatar(
    style=AvatarStyle.CIRCLE,
    background_color="#FFFFFF",
)

# Print available attributes
print("Available attributes:")
print(dir(Avatar))
print("\nAvailable styles:")
print([style.name for style in AvatarStyle])
